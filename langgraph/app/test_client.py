# 표준 라이브러리 임포트
import logging  # 로깅 기능을 위한 모듈

# 타입 힌팅을 위한 임포트
from typing import Any  # 동적 타입을 위한 Any 타입
from uuid import uuid4  # 고유 ID 생성을 위한 UUID 함수

# 서드파티 라이브러리 임포트
import httpx  # 비동기 HTTP 클라이언트

# A2A 클라이언트 관련 임포트
from a2a.client import A2ACardResolver, A2AClient  # A2A 클라이언트와 에이전트 카드 리졸버
from a2a.types import (
    AgentCard,                    # 에이전트 메타데이터를 담는 카드 타입
    MessageSendParams,            # 메시지 전송 파라미터 타입
    SendMessageRequest,           # 동기식 메시지 전송 요청 타입
    SendStreamingMessageRequest,  # 스트리밍 메시지 전송 요청 타입
)


# A2A 프로토콜에서 정의된 표준 경로들
PUBLIC_AGENT_CARD_PATH = '/.well-known/agent.json'  # 공개 에이전트 카드 경로
EXTENDED_AGENT_CARD_PATH = '/agent/authenticatedExtendedCard'  # 인증된 확장 카드 경로


async def main() -> None:
    """
    테스트 클라이언트의 메인 함수
    
    이 함수는 Currency Agent와 통신하는 A2A 클라이언트의 동작을 시연합니다:
    1. 에이전트 카드 가져오기 (공개 및 확장 카드)
    2. 단일 요청-응답 통신
    3. 멀티턴 대화
    4. 스트리밍 응답 처리
    """
    # 로깅 설정: INFO 레벨의 메시지를 표시하도록 구성
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)  # 현재 모듈의 로거 인스턴스 생성

    # --8<-- [start:A2ACardResolver]  # 문서화를 위한 코드 블록 마커

    # 에이전트 서버의 기본 URL
    base_url = 'http://localhost:10000'

    # 비동기 HTTP 클라이언트를 컨텍스트 매니저로 생성
    # with 문을 벗어나면 자동으로 클라이언트가 정리됩니다
    async with httpx.AsyncClient() as httpx_client:
        # A2ACardResolver 초기화
        # 이 리졸버는 에이전트의 메타데이터(카드)를 가져오는 역할을 합니다
        resolver = A2ACardResolver(
            httpx_client=httpx_client,  # HTTP 클라이언트 인스턴스
            base_url=base_url,          # 에이전트 서버의 기본 URL
            # agent_card_path와 extended_agent_card_path는 기본값 사용
        )
        # --8<-- [end:A2ACardResolver]  # 문서화를 위한 코드 블록 마커

        # 공개 에이전트 카드 가져오기 및 클라이언트 초기화
        final_agent_card_to_use: AgentCard | None = None  # 최종적으로 사용할 카드

        try:
            # 공개 에이전트 카드 가져오기 시도
            logger.info(
                f'Attempting to fetch public agent card from: {base_url}{PUBLIC_AGENT_CARD_PATH}'
            )
            # 기본 공개 경로에서 에이전트 카드를 가져옵니다
            _public_card = (
                await resolver.get_agent_card()
            )  # /.well-known/agent.json에서 가져옴
            logger.info('Successfully fetched public agent card:')
            # 카드 내용을 JSON 형식으로 로깅 (None 값 제외, 들여쓰기 2)
            logger.info(
                _public_card.model_dump_json(indent=2, exclude_none=True)
            )
            final_agent_card_to_use = _public_card  # 일단 공개 카드를 사용하도록 설정
            logger.info(
                '\nUsing PUBLIC agent card for client initialization (default).'
            )

            # 확장 카드 지원 여부 확인
            if _public_card.supportsAuthenticatedExtendedCard:
                try:
                    # 인증된 확장 카드 가져오기 시도
                    logger.info(
                        '\nPublic card supports authenticated extended card. '
                        'Attempting to fetch from: '
                        f'{base_url}{EXTENDED_AGENT_CARD_PATH}'
                    )
                    # 인증 헤더 설정 (실제로는 유효한 토큰이 필요함)
                    auth_headers_dict = {
                        'Authorization': 'Bearer dummy-token-for-extended-card'
                    }
                    # 확장 카드 가져오기 - 사용자 정의 경로와 헤더 사용
                    _extended_card = await resolver.get_agent_card(
                        relative_card_path=EXTENDED_AGENT_CARD_PATH,
                        http_kwargs={'headers': auth_headers_dict},
                    )
                    logger.info(
                        'Successfully fetched authenticated extended agent card:'
                    )
                    logger.info(
                        _extended_card.model_dump_json(
                            indent=2, exclude_none=True
                        )
                    )
                    # 확장 카드를 사용하도록 업데이트
                    final_agent_card_to_use = (
                        _extended_card
                    )
                    logger.info(
                        '\nUsing AUTHENTICATED EXTENDED agent card for client '
                        'initialization.'
                    )
                except Exception as e_extended:
                    # 확장 카드 가져오기 실패 시 경고만 표시하고 계속 진행
                    logger.warning(
                        f'Failed to fetch extended agent card: {e_extended}. '
                        'Will proceed with public card.',
                        exc_info=True,  # 스택 트레이스 포함
                    )
            elif (
                _public_card
            ):  # supportsAuthenticatedExtendedCard가 False 또는 None
                logger.info(
                    '\nPublic card does not indicate support for an extended card. Using public card.'
                )

        except Exception as e:
            # 공개 카드조차 가져올 수 없는 경우 치명적 오류
            logger.error(
                f'Critical error fetching public agent card: {e}', exc_info=True
            )
            raise RuntimeError(
                'Failed to fetch the public agent card. Cannot continue.'
            ) from e

        # --8<-- [start:send_message]  # 문서화를 위한 코드 블록 마커
        
        # A2A 클라이언트 초기화
        client = A2AClient(
            httpx_client=httpx_client,  # HTTP 클라이언트
            agent_card=final_agent_card_to_use  # 에이전트 카드 (공개 또는 확장)
        )
        logger.info('A2AClient initialized.')

        # 첫 번째 테스트: 단일 메시지 전송
        # 메시지 페이로드 구성
        send_message_payload: dict[str, Any] = {
            'message': {
                'role': 'user',  # 메시지 발신자 역할
                'parts': [  # 메시지 내용 (여러 파트로 구성 가능)
                    {'kind': 'text', 'text': 'how much is 10 USD in INR?'}
                ],
                'messageId': uuid4().hex,  # 고유 메시지 ID 생성
            },
        }
        # 요청 객체 생성
        request = SendMessageRequest(
            id=str(uuid4()),  # 요청 ID
            params=MessageSendParams(**send_message_payload)  # 메시지 파라미터
        )

        # 동기식 메시지 전송 및 응답 받기
        response = await client.send_message(request)
        # 응답을 JSON 형식으로 출력 (None 값 제외)
        print(response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:send_message]  # 문서화를 위한 코드 블록 마커

        # --8<-- [start:Multiturn]  # 문서화를 위한 코드 블록 마커
        
        # 두 번째 테스트: 멀티턴 대화
        # 첫 번째 메시지: 불완전한 질문
        send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [
                    {
                        'kind': 'text',
                        'text': 'How much is the exchange rate for 1 USD?',  # 대상 통화 누락
                    }
                ],
                'messageId': uuid4().hex,
            },
        }
        request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**send_message_payload_multiturn),
        )

        # 첫 번째 응답 받기
        response = await client.send_message(request)
        print(response.model_dump(mode='json', exclude_none=True))

        # 응답에서 태스크 ID와 컨텍스트 ID 추출
        # 이 ID들은 대화를 이어가는데 필요합니다
        task_id = response.root.result.id
        contextId = response.root.result.contextId

        # 두 번째 메시지: 누락된 정보 제공
        second_send_message_payload_multiturn: dict[str, Any] = {
            'message': {
                'role': 'user',
                'parts': [{'kind': 'text', 'text': 'CAD'}],  # 캐나다 달러로 변환
                'messageId': uuid4().hex,
                'taskId': task_id,      # 이전 태스크 ID 포함
                'contextId': contextId,  # 대화 컨텍스트 ID 포함
            },
        }

        # 두 번째 요청 전송
        second_request = SendMessageRequest(
            id=str(uuid4()),
            params=MessageSendParams(**second_send_message_payload_multiturn),
        )
        second_response = await client.send_message(second_request)
        print(second_response.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:Multiturn]  # 문서화를 위한 코드 블록 마커

        # --8<-- [start:send_message_streaming]  # 문서화를 위한 코드 블록 마커
        
        # 세 번째 테스트: 스트리밍 응답
        # 스트리밍 요청 객체 생성 (첫 번째 테스트와 동일한 페이로드 사용)
        streaming_request = SendStreamingMessageRequest(
            id=str(uuid4()), 
            params=MessageSendParams(**send_message_payload)
        )

        # 스트리밍 응답 시작
        stream_response = client.send_message_streaming(streaming_request)

        # 스트리밍 응답을 비동기적으로 처리
        # 각 청크가 도착하는 대로 출력됩니다
        async for chunk in stream_response:
            print(chunk.model_dump(mode='json', exclude_none=True))
        # --8<-- [end:send_message_streaming]  # 문서화를 위한 코드 블록 마커


# 스크립트 진입점
if __name__ == '__main__':
    import asyncio  # 비동기 실행을 위한 asyncio 임포트

    # 비동기 main 함수 실행
    # asyncio.run()은 이벤트 루프를 생성하고 main()을 실행한 후 정리합니다
    asyncio.run(main())