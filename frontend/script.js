let sessionId = null;

// Автоматическая подгонка высоты textarea под текст
const messageInput = document.getElementById('messageInput');
messageInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
});

// Отправка сообщения при нажатии Enter (Shift+Enter для новой строки)
messageInput.addEventListener('keydown', function (e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Блокировка ввода и кнопки отправки на время отправки сообщения
    const sendButton = document.getElementById('sendButton');
    const input = messageInput;
    sendButton.disabled = true;
    input.disabled = true;

    // Добавление сообщения пользователя в чат
    addMessage('user', message);
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Показ индикатора загрузки
    const loadingId = addMessage('assistant', '<div class="loading"></div>', true);

    try {
        // Отправка POST-запроса на backend
        const response = await fetch('/v1/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                session_id: sessionId,
                message: message
            })
        });

        if (!response.ok) {
            throw new Error(`HTTP ошибка! статус: ${response.status}`);
        }

        const data = await response.json();

        // Сохранение sessionId при первой отправке
        if (!sessionId) {
            sessionId = data.session_id;
        }

        // Обновление сообщения загрузки на фактический ответ ассистента
        const messagesDiv = document.getElementById('messages');
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.innerHTML = `
                <div class="message-bubble">${escapeHtml(data.reply)}</div>
                <div class="meta">Использовано фрагментов: ${data.meta.rag_hits} | Модель: ${data.meta.model}</div>
            `;
        }
    } catch (error) {
        console.error('Ошибка:', error);
        const messagesDiv = document.getElementById('messages');
        const loadingElement = document.getElementById(loadingId);
        if (loadingElement) {
            loadingElement.innerHTML = `
                <div class="message-bubble" style="background: #fee; border-color: #fcc;">
                    Извините, произошла ошибка. Пожалуйста, попробуйте еще раз.
                </div>
            `;
        }
    } finally {
        // Разблокировка ввода и кнопки
        sendButton.disabled = false;
        input.disabled = false;
        input.focus();
    }
}

// Функция добавления сообщения в чат
function addMessage(role, content, isLoading = false) {
    const messagesDiv = document.getElementById('messages');
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const id = `msg-${Date.now()}-${Math.random()}`;
    messageDiv.id = id;

    if (isLoading) {
        messageDiv.innerHTML = `<div class="message-bubble">${content}</div>`;
    } else {
        messageDiv.innerHTML = `<div class="message-bubble">${escapeHtml(content)}</div>`;
    }

    messagesDiv.appendChild(messageDiv);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;

    return id;
}

// Функция экранирования HTML-сущностей для безопасного отображения
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Проверка доступности backend при загрузке страницы
async function checkHealth() {
    try {
        const response = await fetch('/health');
        if (!response.ok) {
            console.error('Проверка состояния сервиса не удалась');
        }
    } catch (error) {
        console.error('Ошибка при проверке состояния сервиса:', error);
    }
}

checkHealth();
