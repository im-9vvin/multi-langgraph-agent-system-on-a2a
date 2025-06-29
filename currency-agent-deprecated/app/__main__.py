# 표준 라이브러리 임포트
import logging  # 로깅 기능을 위한 모듈 - 애플리케이션의 실행 상태와 오류를 기록합니다
import os       # 운영체제 인터페이스 - 환경 변수를 읽기 위해 사용합니다
import sys      # 시스템 관련 기능 - 프로그램 종료 시 에러 코드를 반환하기 위해 사용합니다

# 서드파티 라이브러리 임포트
import click    # 커맨드라인 인터페이스(CLI) 구성을 위한 라이브러리
import httpx    # 비동기 HTTP 클라이언트 - A2A 통신에 사용됩니다
import uvicorn  # ASGI 서버 - FastAPI/Starlette 애플리케이션을 실행합니다

# A2A 프로토콜 관련 임포트
from a2a.server.apps import A2AStarletteApplication  # A2A 프로토콜을 지원하는 Starlette 애플리케이션
from a2a.server.request_handlers import DefaultRequestHandler  # A2A 요청을 처리하는 기본 핸들러
from a2a.server.tasks import InMemoryPushNotifier, InMemoryTaskStore  # 태스크 관리와 푸시 알림을 위한 인메모리 구현체
from a2a.types import (
    AgentCapabilities,  # 에이전트가 지원하는 기능들을 정의 (예: 스트리밍, 푸시 알림)
    AgentCard,         # 에이전트의 메타데이터와 설정을 담는 카드
    AgentSkill,        # 에이전트가 수행할 수 있는 특정 기능/스킬 정의
)
from dotenv import load_dotenv  # .env 파일에서 환경 변수를 로드하는 라이브러리

# 애플리케이션 내부 모듈 임포트
from app.agent import CurrencyAgent  # 통화 변환 기능을 수행하는 LangGraph 에이전트
from app.agent_executor import CurrencyAgentExecutor  # A2A 프로토콜과 에이전트를 연결하는 실행자


# .env 파일에서 환경 변수를 로드합니다
# 이렇게 하면 API 키나 설정값을 코드에 직접 작성하지 않고 안전하게 관리할 수 있습니다
load_dotenv()

# 로깅 설정: INFO 레벨 이상의 모든 로그를 표시합니다
# DEBUG < INFO < WARNING < ERROR < CRITICAL 순서로 심각도가 높아집니다
logging.basicConfig(level=logging.INFO)
# 현재 모듈(__main__)의 로거를 생성합니다
logger = logging.getLogger(__name__)


class MissingAPIKeyError(Exception):
    """
    필수 API 키가 없을 때 발생하는 사용자 정의 예외 클래스
    
    이 예외는 환경 변수에서 필요한 API 키를 찾을 수 없을 때 발생합니다.
    Exception 클래스를 상속받아 구현되었으며, 명확한 에러 메시지를 제공합니다.
    """


@click.command()  # 이 함수를 Click CLI 명령으로 변환합니다
@click.option('--host', 'host', default='localhost')  # --host 옵션: 서버가 바인딩될 호스트 주소
@click.option('--port', 'port', default=10000)       # --port 옵션: 서버가 리스닝할 포트 번호
def main(host, port):
    """
    Currency Agent 서버를 시작하는 메인 함수
    
    이 함수는 다음 작업을 수행합니다:
    1. 필수 환경 변수 확인 (API 키)
    2. 에이전트 카드 및 기능 설정
    3. A2A 서버 초기화 및 실행
    
    Args:
        host (str): 서버 호스트 주소 (기본값: 'localhost')
        port (int): 서버 포트 번호 (기본값: 10000)
    """
    model_source = os.getenv('TOOL)MODEL_SRC', 'openai')
    try:
        # LLM(Large Language Model) 소스 확인 및 필수 환경 변수 검증
        # model_source가 설정되지 않았으면 기본값으로 'google' 사용
        if model_source == 'openai':
            if not os.getenv('TOOL_API_KEY'):
                raise MissingAPIKeyError(
                    'TOOL_API_KEY for "{model_source}" model environment variable not set.'
                )
            os.environ["OPENAI_API_KEY"] = os.getenv("TOOL_API_KEY")

        
        # 에이전트가 지원하는 기능들을 정의합니다
        # streaming: 실시간 스트리밍 응답 지원 (응답이 생성되는 대로 전송)
        # pushNotifications: 클라이언트에게 능동적으로 알림을 보낼 수 있음
        capabilities = AgentCapabilities(streaming=True, pushNotifications=True)
        
        # 에이전트가 제공하는 특정 스킬(기능)을 정의합니다
        skill = AgentSkill(
            id='convert_currency',  # 스킬의 고유 식별자
            name='Currency Exchange Rates Tool',  # 사용자에게 표시될 스킬 이름
            description='Helps with exchange values between various currencies',  # 스킬 설명
            tags=['currency conversion', 'currency exchange'],  # 검색용 태그
            examples=['What is exchange rate between USD and GBP?'],  # 사용 예시
        )
        
        # 에이전트 카드: A2A 프로토콜에서 에이전트를 설명하는 메타데이터
        # 이 정보는 /.well-known/agent.json 엔드포인트를 통해 공개됩니다
        agent_card = AgentCard(
            name='Currency Agent',  # 에이전트 이름
            description='Helps with exchange rates for currencies',  # 에이전트 설명
            url=f'http://{host}:{port}/',  # 에이전트의 기본 URL
            version='1.0.0',  # 에이전트 버전
            defaultInputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,  # 지원하는 입력 타입
            defaultOutputModes=CurrencyAgent.SUPPORTED_CONTENT_TYPES,  # 지원하는 출력 타입
            capabilities=capabilities,  # 위에서 정의한 기능들
            skills=[skill],  # 에이전트가 제공하는 스킬 목록
        )

        # --8<-- [start:DefaultRequestHandler]  # 문서화를 위한 코드 블록 마커
        
        # 비동기 HTTP 클라이언트 생성 - 푸시 알림 전송에 사용됩니다
        httpx_client = httpx.AsyncClient()
        
        # A2A 요청을 처리할 핸들러 생성
        request_handler = DefaultRequestHandler(
            # 실제 에이전트 로직을 실행하는 실행자
            agent_executor=CurrencyAgentExecutor(),
            # 진행 중인 태스크를 메모리에 저장하는 스토어
            # 프로덕션에서는 Redis 등의 영구 저장소 사용을 고려해야 합니다
            task_store=InMemoryTaskStore(),
            # 클라이언트에게 푸시 알림을 보내는 노티파이어
            push_notifier=InMemoryPushNotifier(httpx_client),
        )
        
        # A2A 프로토콜을 지원하는 Starlette 애플리케이션 생성
        server = A2AStarletteApplication(
            agent_card=agent_card,  # 에이전트 메타데이터
            http_handler=request_handler  # 요청 처리 핸들러
        )

        # Uvicorn ASGI 서버로 애플리케이션 실행
        # server.build()는 Starlette 애플리케이션 인스턴스를 반환합니다
        uvicorn.run(server.build(), host=host, port=port)
        # --8<-- [end:DefaultRequestHandler]  # 문서화를 위한 코드 블록 마커

    except MissingAPIKeyError as e:
        # API 키 관련 에러는 사용자가 해결할 수 있으므로 명확한 메시지를 표시
        logger.error(f'Error: {e}')
        # 에러 코드 1로 프로그램 종료 (0이 아닌 값은 에러를 의미)
        sys.exit(1)
    except Exception as e:
        # 예상치 못한 모든 에러를 포착하여 처리
        logger.error(f'An error occurred during server startup: {e}')
        # 에러 코드 1로 프로그램 종료
        sys.exit(1)


# Python 스크립트가 직접 실행될 때만 main() 함수를 호출
# 모듈로 임포트될 때는 실행되지 않습니다
if __name__ == '__main__':
    # Click이 자동으로 커맨드라인 인자를 파싱하고 main 함수에 전달합니다
    main()