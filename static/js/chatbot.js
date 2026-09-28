document.addEventListener('DOMContentLoaded', () => {
    const launcher = document.getElementById('chatbot-launcher');
    const window = document.getElementById('chatbot-window');
    const closeBtn = document.getElementById('close-chat');
    const chatInput = document.getElementById('chat-input');
    const sendBtn = document.getElementById('send-btn');
    const messagesContainer = document.getElementById('chat-messages');
    const typingIndicator = document.getElementById('typing-indicator');

    // Toggle Chat Window
    launcher.addEventListener('click', () => {
        window.classList.toggle('active');
        if (window.classList.contains('active')) {
            chatInput.focus();
        }
    });

    closeBtn.addEventListener('click', () => {
        window.classList.remove('active');
    });

    // Send Message
    const sendMessage = async () => {
        const text = chatInput.value.trim();
        if (!text) return;

        // Add user message
        appendMessage('user', text);
        chatInput.value = '';

        // Show typing indicator
        typingIndicator.classList.remove('hidden');
        scrollToBottom();

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message: text }),
            });

            const data = await response.json();
            
            // Hide typing indicator
            typingIndicator.classList.add('hidden');

            if (data.response) {
                appendMessage('bot', data.response);
            } else {
                appendMessage('bot', "I'm sorry, I'm having trouble responding right now. 🤖");
            }
        } catch (error) {
            console.error('Chat Error:', error);
            typingIndicator.classList.add('hidden');
            appendMessage('bot', "Oops! Something went wrong on my end. Please try again later. 🚜");
        }
    };

    const appendMessage = (sender, text) => {
        const msgDiv = document.createElement('div');
        msgDiv.className = `message ${sender}-message`;
        
        // Format text: convert links and handle newlines
        let formattedText = text;
        
        // 1. Convert Markdown links: [Text](URL)
        formattedText = formattedText.replace(/\[([^\]]+)\]\((https?:\/\/[^\s\)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        
        // 2. Convert plain URLs (not already in href)
        // This regex looks for URLs that aren't preceded by 'href="' or part of an existing <a> tag
        const urlRegex = /(?<!href=")(https?:\/\/[^\s<]+)/g;
        formattedText = formattedText.replace(urlRegex, '<a href="$1" target="_blank">$1</a>');
        
        // 3. Convert **Bold** text
        formattedText = formattedText.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // 4. Convert newlines to <br>
        formattedText = formattedText.replace(/\n/g, '<br>');
        
        msgDiv.innerHTML = `<p>${formattedText}</p>`;
        messagesContainer.appendChild(msgDiv);
        scrollToBottom();
    };

    const scrollToBottom = () => {
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    };

    // Event Listeners
    sendBtn.addEventListener('click', sendMessage);

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            sendMessage();
        }
    });

    // Handle Quick Replies
    document.addEventListener('click', (e) => {
        if (e.target.classList.contains('quick-reply')) {
            const text = e.target.getAttribute('data-msg');
            chatInput.value = text;
            sendMessage();
            // Optional: Hide quick replies after use
            e.target.parentElement.style.display = 'none';
        }
    });
});
