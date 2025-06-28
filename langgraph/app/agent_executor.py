# 표준 라이브러리 임포트
import logging  # 로깅 기능을 위한 모듈

# A2A 프로토콜 관련 임포트
from a2a.server.agent_execution import AgentExecutor, RequestContext  # 에이전트 실행을 위한 기본 클래스들
from a2a.server.events import EventQueue  # 이벤트 기반 통신을 위한 큐
from a2a.server.tasks import TaskUpdater  # 태스크 상태를 업데이트하는 유틸리티
from a2a.types import (
    InternalError,          # 내부 서버 오류를 나타내는 타입
    InvalidParamsError,     # 잘못된 파라미터 오류를 나타내는 타입
    Part,                   # 메시지의 일부를 나타내는 컨테이너 타입
    Task,                   # 태스크 객체 타입
    TaskState,              # 태스크 상태 열거형 (working, input_required, completed 등)
    TextPart,               # 텍스트 콘텐츠를 담는 타입
    UnsupportedOperationError,  # 지원하지 않는 작업 오류 타입
)
from a2a.utils import (
    new_agent_text_message,  # 에이전트 텍스트 메시지를 생성하는 헬퍼 함수
    new_task,               # 새로운 태스크를 생성하는 헬퍼 함수
)
from a2a.utils.errors import ServerError  # 서버 오류를 위한 기본 예외 클래스

# 애플리케이션 내부 모듈 임포트
from app.agent import CurrencyAgent  # 통화 변환 에이전트 클래스


# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CurrencyAgentExecutor(AgentExecutor):
    """
    통화 변환 에이전트 실행자 클래스
    
    이 클래스는 A2A 프로토콜의 AgentExecutor를 상속받아
    CurrencyAgent와 A2A 서버 간의 브리지 역할을 합니다.
    
    주요 역할:
    - A2A 요청을 받아 CurrencyAgent에 전달
    - 에이전트의 응답을 A2A 이벤트로 변환
    - 태스크 상태 관리 및 업데이트
    - 오류 처리 및 예외 관리
    """

    def __init__(self):
        """
        실행자 초기화 메서드
        
        CurrencyAgent 인스턴스를 생성하고 저장합니다.
        """
        # 통화 변환 기능을 수행하는 에이전트 인스턴스 생성
        self.agent = CurrencyAgent()

    async def execute(
        self,
        context: RequestContext,  # 현재 요청의 컨텍스트 정보
        event_queue: EventQueue,  # 이벤트를 전송할 큐
    ) -> None:
        """
        에이전트 실행 메서드
        
        이 메서드는 A2A 요청을 받아 에이전트를 실행하고,
        결과를 이벤트로 변환하여 클라이언트에게 전송합니다.
        
        Args:
            context: 요청 컨텍스트 (사용자 입력, 태스크 정보 등 포함)
            event_queue: 이벤트를 전송할 큐
            
        Raises:
            ServerError: 요청 검증 실패 또는 내부 오류 발생 시
        """
        # 요청 유효성 검증
        error = self._validate_request(context)
        if error:
            # 유효하지 않은 요청인 경우 InvalidParamsError 발생
            raise ServerError(error=InvalidParamsError())

        # 사용자 입력 추출
        query = context.get_user_input()
        
        # 현재 태스크 가져오기 (멀티턴 대화의 경우 기존 태스크가 있을 수 있음)
        task = context.current_task
        if not task:
            # 새로운 대화의 경우 태스크 생성
            task = new_task(context.message)  # type: ignore
            # 태스크 생성 이벤트를 큐에 추가
            await event_queue.enqueue_event(task)
        
        # 태스크 업데이터 생성 - 태스크 상태를 업데이트하는데 사용됩니다
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        
        try:
            # 에이전트의 스트리밍 응답을 비동기적으로 처리
            async for item in self.agent.stream(query, task.contextId):
                # 응답 항목에서 상태 정보 추출
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                # 태스크가 진행 중이고 사용자 입력이 필요하지 않은 경우
                if not is_task_complete and not require_user_input:
                    # "작업 중" 상태로 업데이트하고 진행 메시지 전송
                    await updater.update_status(
                        TaskState.working,  # 태스크 상태를 "작업 중"으로 설정
                        new_agent_text_message(  # 에이전트 메시지 생성
                            item['content'],     # 메시지 내용
                            task.contextId,      # 대화 컨텍스트 ID
                            task.id,            # 태스크 ID
                        ),
                    )
                # 사용자 입력이 필요한 경우
                elif require_user_input:
                    # "입력 필요" 상태로 업데이트하고 안내 메시지 전송
                    await updater.update_status(
                        TaskState.input_required,  # 태스크 상태를 "입력 필요"로 설정
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                        final=True,  # 이것이 이 태스크의 최종 상태임을 표시
                    )
                    break  # 사용자 입력을 기다려야 하므로 루프 종료
                # 태스크가 완료된 경우
                else:
                    # 결과를 아티팩트로 추가
                    # 아티팩트는 태스크의 최종 결과물을 저장하는 방법입니다
                    await updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],  # 텍스트 결과를 Part로 래핑
                        name='conversion_result',  # 아티팩트 이름
                    )
                    # 태스크를 완료 상태로 변경
                    await updater.complete()
                    break  # 태스크 완료되었으므로 루프 종료

        except Exception as e:
            # 예상치 못한 오류 발생 시 로깅하고 InternalError 발생
            logger.error(f'An error occurred while streaming the response: {e}')
            # 원본 예외를 포함하여 ServerError 발생 (디버깅에 유용)
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        """
        요청 검증 메서드
        
        현재는 항상 False를 반환하여 모든 요청을 유효한 것으로 처리합니다.
        실제 구현에서는 여기에 요청 검증 로직을 추가할 수 있습니다.
        
        Args:
            context: 검증할 요청 컨텍스트
            
        Returns:
            bool: 오류가 있으면 True, 유효하면 False
        """
        # TODO: 실제 검증 로직 구현
        # 예: 필수 필드 확인, 입력 형식 검증 등
        return False

    async def cancel(
        self, context: RequestContext, event_queue: EventQueue
    ) -> None:
        """
        태스크 취소 메서드
        
        현재는 지원하지 않는 작업으로 구현되어 있습니다.
        필요한 경우 태스크 취소 로직을 구현할 수 있습니다.
        
        Args:
            context: 취소할 태스크의 컨텍스트
            event_queue: 이벤트를 전송할 큐
            
        Raises:
            ServerError: 항상 UnsupportedOperationError 발생
        """
        # 태스크 취소는 현재 지원하지 않음
        # 필요한 경우 여기에 취소 로직 구현 가능
        raise ServerError(error=UnsupportedOperationError())