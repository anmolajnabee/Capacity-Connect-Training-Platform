import reflex as rx
import base64
import io
import logging
from urllib.parse import quote, urlsplit
import qrcode


def certificate_qr(origin: str, number: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(origin)
        if (
            parsed.scheme not in {"https", "http"}
            or not parsed.netloc
            or parsed.username
            or parsed.password
            or len(origin) > 500
            or not number
            or len(number) > 64
        ):
            raise ValueError(
                "Invalid verification origin or certificate identifier."
            )
        url = (
            f"{parsed.scheme}://{parsed.netloc}/verify/{quote(number, safe='')}"
        )
        image = qrcode.make(url)
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        return (
            url,
            f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}",
        )
    except Exception as e:
        logging.exception(f"Error: {type(e).__name__}")
        raise
