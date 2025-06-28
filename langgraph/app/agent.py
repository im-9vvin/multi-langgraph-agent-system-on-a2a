# 표준 라이브러리 임포트
import os  # 운영체제 인터페이스 - 환경 변수를 읽기 위해 사용합니다

# 타입 힌팅을 위한 임포트
from collections.abc import AsyncIterable  # 비동기 이터러블 타입을 위한 추상 베이스 클래스
from typing import Any, Literal  # 타입 어노테이션을 위한 유틸리티

# 서드파티 라이브러리 임포트
import httpx  # 비동기 HTTP 클라이언트 - 외부 API 호출에 사용됩니다

# LangChain 관련 임포트
from langchain_core.messages import AIMessage, ToolMessage  # LangChain 메시지 타입들
from langchain_core.tools import tool  # 함수를 LangChain 도구로 변환하는 데코레이터
from langchain_google_genai import ChatGoogleGenerativeAI  # Google AI (Gemini) 통합
from langchain_openai import ChatOpenAI  # OpenAI API 호환 모델 통합
from langgraph.checkpoint.memory import MemorySaver  # 대화 상태를 메모리에 저장하는 체크포인터
from langgraph.prebuilt import create_react_agent  # ReAct 패턴의 에이전트를 생성하는 헬퍼 함수
from pydantic import BaseModel  # 데이터 검증과 스키마 정의를 위한 라이브러리


# 전역 메모리 세이버 인스턴스 생성
# 이것은 대화의 상태와 히스토리를 저장하여 멀티턴 대화를 가능하게 합니다
memory = MemorySaver()


@tool  # 이 데코레이터는 함수를 LangChain 도구로 변환합니다
def get_exchange_rate(
    currency_from: str = 'USD',  # 변환할 통화 (기본값: 미국 달러)
    currency_to: str = 'EUR',    # 변환 대상 통화 (기본값: 유로)
    currency_date: str = 'latest',  # 환율 날짜 (기본값: 최신)
):
    """
    현재 환율을 가져오는 도구 함수
    
    이 함수는 Frankfurter API를 사용하여 실시간 환율 정보를 제공합니다.
    LangChain의 @tool 데코레이터로 래핑되어 있어 에이전트가 사용할 수 있습니다.

    Args:
        currency_from: 변환할 통화 코드 (예: "USD")
        currency_to: 변환 대상 통화 코드 (예: "EUR")
        currency_date: 환율 날짜 또는 "latest". 기본값은 "latest"

    Returns:
        환율 데이터를 담은 딕셔너리, 또는 오류 발생 시 에러 메시지
    """
    try:
        # Frankfurter API에 HTTP GET 요청을 보냅니다
        # API URL 구조: https://api.frankfurter.app/{날짜}?from={통화1}&to={통화2}
        response = httpx.get(
            f'https://api.frankfurter.app/{currency_date}',
            params={'from': currency_from, 'to': currency_to},
        )
        # HTTP 상태 코드가 4xx 또는 5xx인 경우 예외를 발생시킵니다
        response.raise_for_status()

        # JSON 응답을 파싱합니다
        data = response.json()
        # API 응답 형식 검증
        if 'rates' not in data:
            return {'error': 'Invalid API response format.'}
        return data
    except httpx.HTTPError as e:
        # HTTP 요청 관련 오류 처리
        return {'error': f'API request failed: {e}'}
    except ValueError:
        # JSON 파싱 오류 처리
        return {'error': 'Invalid JSON response from API.'}


class ResponseFormat(BaseModel):
    """
    에이전트 응답 형식을 정의하는 Pydantic 모델
    
    이 모델은 구조화된 응답을 보장하여 클라이언트가 응답 상태를
    일관되게 파싱할 수 있도록 합니다.
    
    Attributes:
        status: 응답 상태를 나타내는 리터럴 타입
            - 'input_required': 사용자로부터 추가 입력이 필요함
            - 'completed': 요청이 성공적으로 완료됨
            - 'error': 처리 중 오류가 발생함
        message: 사용자에게 전달할 메시지 내용
    """
    status: Literal['input_required', 'completed', 'error'] = 'input_required'
    message: str


class CurrencyAgent:
    """
    통화 변환 전문 에이전트 클래스
    
    이 클래스는 LangGraph의 ReAct 에이전트 패턴을 사용하여
    통화 변환 관련 질문에 답변하는 특화된 에이전트를 구현합니다.
    
    주요 기능:
    - 환율 조회 도구를 사용한 실시간 환율 정보 제공
    - 구조화된 응답 형식을 통한 일관된 응답
    - 멀티턴 대화 지원
    - 스트리밍 응답 지원
    """

    # 에이전트의 시스템 프롬프트 - 에이전트의 역할과 제한사항을 정의합니다
    SYSTEM_INSTRUCTION = (
        'You are a specialized assistant for currency conversions. '
        "Your sole purpose is to use the 'get_exchange_rate' tool to answer questions about currency exchange rates. "
        'If the user asks about anything other than currency conversion or exchange rates, '
        'politely state that you cannot help with that topic and can only assist with currency-related queries. '
        'Do not attempt to answer unrelated questions or use tools for other purposes.'
    )

    # 응답 형식에 대한 지시사항 - 구조화된 응답을 생성하도록 안내합니다
    FORMAT_INSTRUCTION = (
        'Set response status to input_required if the user needs to provide more information to complete the request.'
        'Set response status to error if there is an error while processing the request.'
        'Set response status to completed if the request is complete.'
    )

    def __init__(self):
        """
        에이전트 초기화 메서드
        
        환경 변수를 기반으로 적절한 LLM을 선택하고,
        도구와 함께 ReAct 에이전트 그래프를 생성합니다.
        """
        # LLM 소스 확인 - 기본값은 'google'
        model_source = os.getenv('model_source', 'google')
        
        if model_source == 'google':
            # Google AI (Gemini) 모델 사용
            # gemini-2.0-flash는 빠른 응답을 위한 경량 모델입니다
            self.model = ChatGoogleGenerativeAI(model='gemini-2.0-flash')
        else:
            # 커스텀 OpenAI 호환 서버 사용 (예: local LLM, Azure OpenAI 등)
            self.model = ChatOpenAI(
                model=os.getenv('TOOL_LLM_NAME'),  # 모델 이름
                openai_api_key=os.getenv('API_KEY', 'EMPTY'),  # API 키 (로컬 서버의 경우 더미값)
                openai_api_base=os.getenv('TOOL_LLM_URL'),  # API 엔드포인트 URL
                temperature=0,  # 온도 0은 더 일관된 응답을 생성합니다
            )
        
        # 에이전트가 사용할 도구 목록
        self.tools = [get_exchange_rate]

        # ReAct 패턴의 에이전트 그래프 생성
        # ReAct = Reasoning + Acting: 추론하고 행동하는 패턴
        self.graph = create_react_agent(
            self.model,  # 사용할 언어 모델
            tools=self.tools,  # 에이전트가 사용할 도구들
            checkpointer=memory,  # 대화 상태를 저장할 체크포인터
            prompt=self.SYSTEM_INSTRUCTION,  # 시스템 프롬프트
            response_format=(self.FORMAT_INSTRUCTION, ResponseFormat),  # 구조화된 응답 형식
        )

    async def stream(self, query, context_id) -> AsyncIterable[dict[str, Any]]:
        """
        사용자 쿼리를 스트리밍 방식으로 처리하는 비동기 메서드
        
        이 메서드는 에이전트의 처리 과정을 실시간으로 스트리밍하여
        사용자에게 진행 상황을 알려줍니다.
        
        Args:
            query: 사용자의 질문 또는 요청
            context_id: 대화 컨텍스트를 식별하는 ID (멀티턴 대화 지원)
            
        Yields:
            처리 상태와 내용을 담은 딕셔너리
        """
        # 입력 메시지 구성 - LangGraph 형식에 맞춰 준비
        inputs = {'messages': [('user', query)]}
        # 설정 구성 - thread_id는 대화 세션을 식별합니다
        config = {'configurable': {'thread_id': context_id}}

        # 에이전트 그래프를 스트리밍 모드로 실행
        # stream_mode='values'는 각 단계의 전체 상태를 반환합니다
        for item in self.graph.stream(inputs, config, stream_mode='values'):
            # 가장 최근 메시지를 가져옵니다
            message = item['messages'][-1]
            
            # AI가 도구를 호출하려고 하는 경우
            if (
                isinstance(message, AIMessage)  # AI 메시지인지 확인
                and message.tool_calls  # 도구 호출이 있는지 확인
                and len(message.tool_calls) > 0  # 도구 호출이 실제로 있는지 확인
            ):
                # 도구 호출 중임을 알리는 메시지 전송
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Looking up the exchange rates...',
                }
            # 도구 실행 결과 메시지인 경우
            elif isinstance(message, ToolMessage):
                # 도구 실행 완료를 알리는 메시지 전송
                yield {
                    'is_task_complete': False,
                    'require_user_input': False,
                    'content': 'Processing the exchange rates..',
                }

        # 모든 처리가 완료된 후 최종 응답 생성
        yield self.get_agent_response(config)

    def get_agent_response(self, config):
        """
        에이전트의 최종 응답을 구성하는 메서드
        
        구조화된 응답을 기반으로 A2A 프로토콜에 맞는
        응답 형식을 생성합니다.
        
        Args:
            config: 현재 대화 세션의 설정
            
        Returns:
            상태와 내용을 포함한 응답 딕셔너리
        """
        # 현재 그래프 상태를 가져옵니다
        current_state = self.graph.get_state(config)
        # 구조화된 응답 객체를 추출합니다
        structured_response = current_state.values.get('structured_response')
        
        # 구조화된 응답이 있고 올바른 타입인 경우
        if structured_response and isinstance(
            structured_response, ResponseFormat
        ):
            # 상태에 따라 적절한 응답 구성
            if structured_response.status == 'input_required':
                # 추가 입력이 필요한 경우
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'error':
                # 오류가 발생한 경우
                return {
                    'is_task_complete': False,
                    'require_user_input': True,
                    'content': structured_response.message,
                }
            if structured_response.status == 'completed':
                # 성공적으로 완료된 경우
                return {
                    'is_task_complete': True,
                    'require_user_input': False,
                    'content': structured_response.message,
                }

        # 구조화된 응답을 가져올 수 없는 경우의 폴백 응답
        return {
            'is_task_complete': False,
            'require_user_input': True,
            'content': (
                'We are unable to process your request at the moment. '
                'Please try again.'
            ),
        }

    # 에이전트가 지원하는 콘텐츠 타입 목록
    # A2A 프로토콜에서 에이전트의 입출력 형식을 명시하는데 사용됩니다
    SUPPORTED_CONTENT_TYPES = ['text', 'text/plain']