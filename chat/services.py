# Standard library
import os
import uuid


# Django / third-party
import PyPDF2
from storages.backends.s3boto3 import S3Boto3Storage
from django.conf import settings

# Local app imports
from .models import Message
from .ai_models import AIModelManager

chat_uploads = S3Boto3Storage(bucket_name=settings.BUCKET_CHAT_UPLOADS)


# Message/Chat Detail Service Handling
class ChatService:
    def __init__(self):
        self.ai_manager = AIModelManager()

    def process_file(self, uploaded_file):
        if not uploaded_file:
            return "" ""

        file_name = uploaded_file.name
        file_ext = os.path.splitext(file_name)[1].lower()[1:]
        file_content = ""

        try:
            if file_ext == "pdf":
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                file_content = "\n\n".join(
                    page.extract_text() for page in pdf_reader.pages
                )
            elif file_ext in ["txt", "md", "py", "js", "html", "css", "json"]:
                file_content = uploaded_file.read().decode("utf-8")
                uploaded_file.seek(0)

            file_info = f"\n\nI've uploaded a file: {file_name}"
            if file_content:
                file_info += "\n\nFile content:\n```\n" + file_content[:20000] + "\n```"
                if len(file_content) > 20000:
                    file_info += "\n(File content truncated due to length)"

            return file_info, file_content
        except Exception as e:
            return f"Error processing file: {str(e)}", ""

    def save_file(self, chat_id, uploaded_file):
        if uploaded_file:
            ext = uploaded_file.name.split(".")[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"
            path = f"{chat_id}/{filename}"
            return chat_uploads.save(path, uploaded_file)
        return None

    def create_message(self, chat, role, content):
        return Message.objects.create(chat=chat, role=role, content=content)

    def get_chat_history(self, chat, limit=10):
        return list(chat.messages.all().order_by("created_at"))[-limit:]

    # def update_chat_title(self, chat, title_text=None):
    #     if not title_text:
    #         return
    #     chat.title = title_text[:50] + ("..." if len(title_text) > 50 else "")
    #     chat.save()

    # def generate_response(self, user):
    #     messages = [{"role": "user", "content": user}]
    #     response = self.ai_manager.get_chat_completion(messages)
    #     return response
