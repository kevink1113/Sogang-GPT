from django.contrib.auth import authenticate
from django.shortcuts import redirect, render
from drf_yasg import openapi
from rest_framework.authtoken.models import Token
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .crawl_saint import get_saint_cookies
from .auth_backend import PasswordlessAuthBackend

import openai
from chatbot.secret import get_secret
from chatbot.api import *

from django.contrib.auth import login as auth_login
from typing_extensions import override
from openai.types.beta.threads.runs import ToolCall, RunStep

from openai.types.beta.assistant_stream_event import (
    ThreadRunRequiresAction, ThreadMessageDelta, ThreadRunCompleted,ThreadMessageCompleted,
    ThreadRunFailed, ThreadRunCancelling, ThreadRunCancelled, ThreadRunExpired, ThreadRunStepFailed,
    ThreadRunStepCancelled)
# from backend.chatbot import chatbot_function_call
# from chatbot import chatbot_function_call
from chatbot.chatbot import chatbot_function_call

client = openai.OpenAI(api_key=get_secret())

from drf_yasg.utils import swagger_auto_schema
import openai
from openai import AssistantEventHandler

from chatbot.chatbot import chatbot_query
from chatbot.chatbot import chatbot_query_stream
from chatbot.secret import get_secret
from chatbot.api import *

from django.http import StreamingHttpResponse, JsonResponse
from rest_framework.decorators import api_view, permission_classes
import json

class LoginView(APIView):
    """
    post:
    사용자 로그인(회원가입)을 위한 엔드포인트

    username과 password를 JSON 형태로 전달받아 인증을 수행
    인증에 성공하면, 사용자 토큰을 반환

    요청 예시:
    {
        "username": "2019xxxx",
        "password": "password123"
    }

    응답 예시:
    {
        "token": "1234567890abcdef"
    }
    """

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'username': openapi.Schema(type=openapi.TYPE_STRING, description='학번'),
            'password': openapi.Schema(type=openapi.TYPE_STRING, description='비밀번호')
        }
        # response 정의

    ))
    # @swagger_auto_schema(operation_description="POST 요청을 위한 엔드포인트입니다.")
    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')
        # print(username, password)
        cookies = get_saint_cookies(username, password)
        if cookies is None:
            return Response({'error': 'Invalid Credentials or Saint Cookies not retrieved'},
                            status=status.HTTP_400_BAD_REQUEST)

        user = PasswordlessAuthBackend().authenticate(username=username, cookies=cookies)
        if user is None:
            return Response({'error': 'Authentication Failed'}, status=status.HTTP_404_NOT_FOUND)

        auth_login(request, user, backend='backend.auth_backend.PasswordlessAuthBackend')  # Django login

        # 토큰이 이미 존재하면 가져오고, 그렇지 않으면 생성합니다.
        token, created = Token.objects.get_or_create(user=user)
        print("Token: ", token.key, "Created: ", created)
        # 'created' 변수는 토큰이 새로 생성되었는지 여부를 나타냅니다.
        # 여기서 추가적인 로직을 구현할 수 있습니다 (예: 로그 생성).

        print(user.username, user.name, user.state, user.year, user.semester, user.major, user.advisor, user.nickname)

        return Response({'token': token.key,  # 토큰
                         'username': user.username,  # 학번
                         'name': user.name,  # 이름
                         'state': user.state,  # 0: 재학, 1: 휴학, 2: 졸업
                         'year': user.year,  # 학년
                         'semester': user.semester,  # 학기
                         'major': user.major,  # 전공
                         'advisor': user.advisor,  # 지도교수
                         'nickname': user.nickname,  # 닉네임
                         },
                        status=status.HTTP_200_OK)


def my_login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        cookies = get_saint_cookies(username, password)
        if cookies is None:
            return render(request, 'login.html')
        user = PasswordlessAuthBackend().authenticate(username=username, cookies=cookies)
        # login 함수 호출
        auth_login(request, user)
        return redirect('/')
    else:
        # GET 요청 처리
        pass
    return render(request, 'login.html')


def offline(request):
    return render(request, 'offline.html')

def cancel_active_runs(client, thread_id):
    """
    명시된 thread에서 실행중인 모든 run을 취소하는 함수

    :param client: 사용할 OpenAI client
    :param thread_id: 실행중인 active run(들)이 있는 thread ID
    """

    active_runs = client.beta.threads.runs.list(thread_id=thread_id).data
    for run in active_runs:
        if run.status not in ["completed", "failed", "cancelled", "expired"]: # 취소된 run은 다시 취소하지 않음
            client.beta.threads.runs.cancel(thread_id=thread_id, run_id=run.id)
            print(f"Cancelled run {run.id}")


class ChatView(APIView):
    """
    post:
    챗봇 구현 예시
    요청 예시:
    {
        "question": "아메리카노와 에스프레소의 차이에 대해 알려줘"
    }
    """
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(request_body=openapi.Schema(
        type=openapi.TYPE_OBJECT,
        properties={
            'question': openapi.Schema(type=openapi.TYPE_STRING, description='질문')
        }
        # response 정의
    ))
    # def post(self, request, *args, **kwargs):
    #     user = request.user

    #     print(user)
    #     print("Question: ", request.data.get('question'))

    #     question = request.data.get('question')
    #     assistant_id = "asst_fSEoeHlDpbVT7NA4chr18jLM"
    #     thread_id = user.thread

    #     chatbot_query_stream(assistant_id, user, thread_id, question)

    #     recent_question = messages.data[1].content[0].text.value
    #     recent_answer = messages.data[0].content[0].text.value

    #     print(recent_question)
    #     print(recent_answer)
    #     return Response({'answer': recent_answer},
    #                     status=status.HTTP_200_OK)

    def post(self, request, *args, **kwargs):
        user = request.user
        question = request.data.get('question')
        assistant_id = "asst_fSEoeHlDpbVT7NA4chr18jLM"
        thread_id = user.thread
        
        cancel_active_runs(client, thread_id)

        def event_stream():
            handler = EventHandler(thread_id=thread_id, assistant_id=assistant_id, user=user)
            # Initialize the streaming process
            # 질문 보내기
            client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=question
            )
            # 스트림으로 받기
            with client.beta.threads.runs.stream(
                    thread_id=thread_id,
                    assistant_id=assistant_id,
                    event_handler=handler,
            ) as stream:
                try:
                    # Yield data as server-sent events
                    for event in stream:
                        if isinstance(event, ThreadMessageDelta):
                            # 메시지 델타 이벤트 처리
                            data = event.data.delta.content
                            for text in data:
                                print(text.text.value, end='')
                                yield f"data: {json.dumps({'text': text.text.value})}\n\n"
                                # yield "data: run_writing\n\n"
                                # yield text.text.value 
                            # yield f"data: {'text_update': event.data.delta.content}\n\n"
                        # elif isinstance(event, ThreadMessageCompleted):
                            # 메시지 완료 이벤트 처리

                            # yield f"data: {'text': event.data.content}\n\n"
                        elif isinstance(event, ThreadRunCompleted):
                            # 실행 완료 이벤트 처리
                            yield "data: run_completed\n\n"
                        # else:
                        #     # 처리하지 못한 이벤트 타입 로깅
                        #     print(f"Unhandled event type: {type(event)}")
                        #     yield f"data: {json.dumps({'error': 'Unhandled event type'})}\n\n"

                except GeneratorExit:
                    # Handle the case when the client disconnects
                    stream.close()

        # Return a StreamingHttpResponse that keeps the connection open
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        response['Cache-Control'] = 'no-cache'
        return response

class EventHandler(AssistantEventHandler):
    def __init__(self, thread_id, assistant_id, user):
        super().__init__()
        self.thread_id = thread_id
        self.assistant_id = assistant_id
        self.run_id = None
        self.user = user
        self.tool_outputs = []

    @override
    def on_text_created(self, text) -> None:
        print(f"\n서강gpt > ", end="", flush=True)

    @override
    def on_text_delta(self, delta, snapshot):
        print(delta.value, end="", flush=True)

    @override
    def on_tool_call_done(self, tool_call: ToolCall):
        # run 참조
        run = client.beta.threads.runs.retrieve(
            thread_id=self.thread_id,
            run_id=self.run_id)
        # 처음 tool_call에서 모든 tool_call을 처리
        if run.status == "requires_action":
            tools = run.required_action.submit_tool_outputs.tool_calls
            for tool in tools:
                tool_id = tool.id
                function_args = tool.function.arguments
                function_name = tool.function.name
                data = ""

                #함수 하드 코딩 안 하는 방법이 있긴 한데, 좀 가독성이 구려서 그냥 하드코딩 합시다.
                if function_name == "get_user_info":
                    data = get_user_info(self.user.username)
                elif function_name == "get_course_info":
                    data = get_course_info()
                elif function_name == "get_takes_info":
                    data = get_takes_info(self.user.username)
                self.tool_outputs.append({
                    "tool_call_id": tool_id,
                    "output": json.dumps(data)
                })
            #스트림으로 보내기
            with client.beta.threads.runs.submit_tool_outputs_stream(
                    thread_id=self.thread_id,
                    run_id=self.run_id,
                    tool_outputs=self.tool_outputs,
                    event_handler=EventHandler(self.thread_id, self.assistant_id, self.user)
            ) as stream:
                stream.until_done()

    @override
    def on_run_step_created(self, run_step: RunStep):
        # run_id 저장
        self.run_id = run_step.run_id


class StreamView(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        user = request.user
        assistant_id = "asst_fSEoeHlDpbVT7NA4chr18jLM"
        thread_id = user.thread  # Ensure user has a 'thread' attribute or handle accordingly
        question = request.data.get('question', '')

        # Setup OpenAI client
        client = openai.OpenAI(api_key=get_secret())

        # Create a message in the thread
        client.beta.threads.messages.create(
            thread_id=thread_id,
            role="user",
            content=question
        )

        def event_stream():
            # Stream the thread's run
            with client.beta.threads.runs.stream(thread_id=thread_id, assistant_id=assistant_id) as stream:
                for event in stream:
                    # Handle different types of events
                    if hasattr(event, 'status'):
                        if event.status == "completed":
                            break
                        elif event.status == "requires_action":
                            # Handle action required status
                            chatbot_function_call(event, assistant_id, user, thread_id)
                    # Send back text updates
                    if hasattr(event, 'content') and 'text' in event.content:
                        text = event.content['text']
                        yield f"data: {json.dumps({'text': text})}\n\n"

        # Set headers to notify the client that this is an event-stream.
        return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
