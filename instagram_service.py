# instagram_service.py
import requests
import json
import os
import google.generativeai as genai
from datetime import datetime, timedelta

class InstagramMessageHandler:
    def __init__(self, project):
        self.project = project
        self.instagram_token = project.instagram_token
        self.gemini_api_key = project.api_key or os.getenv('GEMINI_API_KEY', '')
        self.bot_prompt = project.bot_prompt
        self.bot_message = project.bot_message
        self.temperature = project.temperature
        self.max_tokens = project.max_tokens
        self.message_buffer = project.message_buffer
        
        # Инициализация Gemini
        genai.configure(api_key=self.gemini_api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        
    def get_instagram_messages(self):
        """Получает новые сообщения из Instagram"""
        if not self.instagram_token:
            print("Instagram токен не настроен")
            return []
            
        # Базовый URL для Instagram Graph API
        base_url = "https://graph.instagram.com/v18.0"
        
        try:
            # Получаем ID пользователя
            me_response = requests.get(f"{base_url}/me", params={
                "access_token": self.instagram_token,
                "fields": "id,username"
            })
            me_data = me_response.json()
            user_id = me_data.get("id")
            
            if not user_id:
                print("Не удалось получить ID пользователя Instagram")
                return []
                
            # Получаем входящие сообщения
            # Примечание: Этот эндпоинт требует дополнительных разрешений от Instagram
            inbox_response = requests.get(f"{base_url}/{user_id}/conversations", params={
                "access_token": self.instagram_token,
                "fields": "participants,messages{message,from,to,created_time}"
            })
            
            return inbox_response.json().get("data", [])
            
        except Exception as e:
            print(f"Ошибка при получении сообщений Instagram: {str(e)}")
            return []
    
    def process_messages(self):
        """Обрабатывает сообщения и отправляет ответы"""
        if self.project.disable_agent:
            cutoff_time = datetime.utcnow() - timedelta(hours=self.project.agent_timeout)
            if self.project.date_created > cutoff_time:
                print("Бот остановлен пользователем")
                return
        
        messages = self.get_instagram_messages()
        for conversation in messages:
            self._process_conversation(conversation)
    
    def _process_conversation(self, conversation):
        """Обрабатывает одну беседу"""
        messages = conversation.get("messages", {}).get("data", [])
        if not messages:
            return
            
        # Отфильтровываем только входящие сообщения (не от нас)
        our_id = conversation.get("participants", {}).get("data", [{}])[0].get("id")
        incoming_messages = [
            msg for msg in messages 
            if msg.get("from", {}).get("id") != our_id
        ]
        
        # Берем только последние N сообщений (согласно буферу)
        recent_messages = incoming_messages[:self.message_buffer]
        
        if not recent_messages:
            return
            
        # Создаем контекст для Gemini
        context = self._prepare_context(recent_messages)
        
        # Получаем ответ от Gemini
        response = self._get_gemini_response(context)
        
        # Отправляем ответ
        if response:
            self._send_instagram_reply(
                conversation.get("id"), 
                recent_messages[0].get("from", {}).get("id"),
                response
            )
    
    def _prepare_context(self, messages):
        """Подготавливает контекст для Gemini"""
        context = f"{self.bot_prompt}\n\n"
        context += "Последние сообщения пользователя:\n"
        
        for msg in reversed(messages):
            context += f"Пользователь: {msg.get('message', '')}\n"
            
        return context
    
    def _get_gemini_response(self, context):
        """Получает ответ от Gemini"""
        try:
            generation_config = {
                "temperature": self.temperature,
                "max_output_tokens": self.max_tokens,
            }
            
            response = self.model.generate_content(
                context,
                generation_config=generation_config
            )
            
            return response.text
            
        except Exception as e:
            print(f"Ошибка при получении ответа от Gemini: {str(e)}")
            return None
    
    def _send_instagram_reply(self, conversation_id, recipient_id, message):
        """Отправляет ответ в Instagram DM"""
        if not self.instagram_token:
            print("Instagram токен не настроен")
            return False
            
        try:
            # Базовый URL для Instagram Graph API
            base_url = "https://graph.instagram.com/v18.0"
            
            # Отправляем сообщение
            response = requests.post(f"{base_url}/{conversation_id}/messages", data={
                "access_token": self.instagram_token,
                "recipient": recipient_id,
                "message": message
            })
            
            data = response.json()
            if data.get("id"):
                print(f"Сообщение успешно отправлено: {data.get('id')}")
                return True
            else:
                print(f"Ошибка при отправке сообщения: {data}")
                return False
                
        except Exception as e:
            print(f"Ошибка при отправке ответа в Instagram: {str(e)}")
            return False