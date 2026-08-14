import httpx
from loguru import logger
from core.config import settings

async def send_telegram_alert(chat_id: int | str, message: str, image_url: str = None):
    """
    Hàm gửi tin nhắn và ảnh báo động qua Telegram Bot API.
    """
    if not settings.TELEGRAM_BOT_TOKEN:
        logger.warning("Chưa cấu hình TELEGRAM_BOT_TOKEN. Bỏ qua gửi cảnh báo Telegram.")
        return
        
    bot_token = settings.TELEGRAM_BOT_TOKEN
    
    # Dùng API sendPhoto nếu có link ảnh, ngược lại dùng sendMessage
    if image_url:
        url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
        payload = {
            "chat_id": chat_id,
            "photo": image_url,
            "caption": message,
            "parse_mode": "HTML" # Hỗ trợ in đậm, in nghiêng cho đẹp
        }
    else:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": message,
            "parse_mode": "HTML"
        }

    try:
        # Sử dụng httpx để gọi API bất đồng bộ (không làm nghẽn FastAPI)
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            logger.info(f"Đã bắn cảnh báo Telegram thành công tới Chat ID: {chat_id}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi Telegram Alert: {str(e)}")