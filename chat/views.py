# Standard library
import time
import json

# Django / third-party
from django.shortcuts import render, redirect, get_object_or_404
from django.http import StreamingHttpResponse, JsonResponse
from django.contrib.auth.decorators import login_required
from django.views import View
from django.utils.decorators import method_decorator
from groq import Groq  # Groq client
from django.conf import settings
from django.core.cache import cache


# Local app imports
from .models import Chat, Message
from .services import ChatService

# Initialize the Chat service.
chat_service = ChatService()

# Initialize the Groq client.
groq_client = Groq()


# Chat Views
@method_decorator(login_required, name="dispatch")
class ChatView(View):
    template_name = "chat/chat.html"

    def get(self, request, chat_id=None):
        # Handle AJAX requests for message updates
        if request.headers.get("X-Requested-With") == "XMLHttpRequest" and chat_id:
            try:
                chat = Chat.objects.get(id=chat_id, user=request.user)
                messages = list(
                    chat.messages.all().order_by("created_at").values("role", "content")
                )
                return JsonResponse({"messages": messages})
            except Chat.DoesNotExist:
                return JsonResponse({"error": "Chat not found"}, status=404)

        chats = Chat.objects.filter(user=request.user).order_by("-updated_at")
        is_new_chat = request.path == "/chat/new/"

        # Handle new chat
        if is_new_chat:
            temp_id = f"temp_{int(time.time())}"
            return render(
                request,
                self.template_name,
                {
                    "current_chat": {"id": temp_id, "title": "New Chat"},
                    "conversation": [],
                    "chats": chats,
                    "is_new_chat": True,
                },
            )

        # Handle existing chat
        if chat_id:
            try:
                chat = Chat.objects.get(id=chat_id, user=request.user)

                # Caching chat conversation
                cache_key = f"chat_conversation:{chat_id}"
                conversation = cache.get(cache_key)

                if conversation:
                    # print hit cache
                    print(f"Cache HIT: {cache_key}")
                else:
                    # print miss cache
                    print(f"Cache MISS: {cache_key}")
                    messages = chat.messages.all().order_by("created_at")
                    conversation = [
                        {"role": msg.role, "text": msg.content} for msg in messages
                    ]
                    # simpan ke cache (misal 5 menit)
                    cache.set(cache_key, conversation, timeout=300)

                return render(
                    request,
                    self.template_name,
                    {
                        "current_chat": chat,
                        "conversation": conversation,
                        "chats": chats,
                        "is_new_chat": False,
                    },
                )
            except Chat.DoesNotExist:
                return redirect("new_chat")

        # Default to chat list or new chat
        return redirect("new_chat")


# Chat Stream View / Chat Detail
@method_decorator(login_required, name="dispatch")
class ChatStreamView(View):
    def post(self, request, chat_id):
        try:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
            prompt_text = request.POST.get("prompt", "").strip()
            uploaded_file = request.FILES.get("file")

            # Process file if present
            file_content = chat_service.process_file(uploaded_file)

            # Create user message - only show file name if file was uploaded
            user_message = prompt_text
            if uploaded_file:
                chat_service.save_file(chat.id, uploaded_file)
                file_indicator = f"\n[Uploaded file: {uploaded_file.name}]"
                user_message += file_indicator

            chat_service.create_message(chat, "user", user_message)

            # For the LLM, combine prompt with actual file content
            full_prompt = prompt_text
            if file_content:
                full_prompt += f"\n\nFile content:\n{file_content}"

            # Update chat title if needed
            if chat.title == "New Chat" and prompt_text:
                chat_service.update_chat_title(chat, prompt_text)

            # Get system prompt and prepare messages for LLM
            system_prompt = request.session.get("system_prompt", settings.SYSTEM_PROMPT)
            messages = [{"role": "system", "content": system_prompt}]
            chat_history = chat_service.get_chat_history(chat)
            messages.extend(
                [
                    {"role": msg.role, "content": msg.content}
                    for msg in chat_history[:-1]
                ]
            )  # Exclude the last message

            # Add the last message with full content for LLM
            messages.append({"role": "user", "content": full_prompt})

            # Stream response
            return self.stream_response(chat, messages)

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    def stream_response(self, chat, messages):
        def event_stream():
            try:
                accumulated_response = ""
                stream = chat_service.ai_manager.get_chat_completion(messages)

                for chunk in stream:
                    content = chunk.choices[0].delta.content

                    if content:
                        accumulated_response += content
                        yield f"data: {json.dumps({'type': 'content', 'content': content})}\n\n"

                if accumulated_response:
                    chat_service.create_message(chat, "assistant", accumulated_response)
                    yield f"data: {json.dumps({'type': 'done'})}\n\n"

            except Exception as e:
                yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        response = StreamingHttpResponse(
            event_stream(), content_type="text/event-stream"
        )
        response["Cache-Control"] = "no-cache"
        response["X-Accel-Buffering"] = "no"
        return response


# Function Create Chat
@login_required
def create_chat(request):
    if request.method == "POST":

        message = request.POST.get("prompt", "").strip()

        if not message:
            return JsonResponse(
                {"success": False, "error": "No message provided"}, status=400
            )

        try:
            # Create new chat with trimmed message as title
            chat = Chat.objects.create(
                user=request.user,
                title=message[:30] + "..." if len(message) > 30 else message,
            )

            # Create initial message
            Message.objects.create(chat=chat, content=message.strip(), role="user")

            return JsonResponse(
                {
                    "success": True,
                    "chat_id": chat.id,
                    "redirect_url": f"/chat/{chat.id}/",
                }
            )

        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)

    return JsonResponse(
        {"success": False, "error": "Invalid request method"}, status=405
    )


# Function Delete Chat
@login_required
def delete_chat(request, chat_id):
    if request.method == "POST":
        try:
            chat = get_object_or_404(Chat, id=chat_id, user=request.user)
            chat.delete()
            return JsonResponse({"status": "success"})
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)


# Function Update Title Chat
@login_required
def update_chat_title(request, chat_id):
    if request.method == "POST":
        chat = get_object_or_404(Chat, id=chat_id, user=request.user)
        data = json.loads(request.body)
        new_title = data.get("title", "").strip()
        if new_title:
            chat.title = new_title
            chat.save()
            return JsonResponse({"success": True})
        return JsonResponse({"error": "Title is required"}, status=400)
    return JsonResponse({"error": "Method not allowed"}, status=405)
