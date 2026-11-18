"""Human-entered portal challenges; image decoding never recognizes text."""
from dataclasses import dataclass, field
import secrets
import io
from PIL import Image
from core.portal_client import PortalError

def png_image(content: bytes) -> bytes:
    try:
        with Image.open(io.BytesIO(content)) as image:
            if image.width*image.height>2000000: raise ValueError('CAPTCHA image is too large')
            image.load();out=io.BytesIO();image.convert('RGB').save(out,'PNG');return out.getvalue()
    except Exception as exc:
        raise PortalError('NETWORK ERROR','CAPTCHA image could not be decoded. Refresh the image or check the portal connection.') from exc

@dataclass
class Challenge:
    image: bytes
    attempts: int = 0
    token: str = field(default_factory=lambda:secrets.token_hex(12))
    def failed(self) -> bool:
        self.attempts += 1
        return self.attempts >= 3
