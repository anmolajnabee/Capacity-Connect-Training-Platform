import reflex as rx
import logging
import unicodedata
from urllib.parse import unquote
from sqlalchemy import text
from app.services.certificate_qr import certificate_qr


class CertificateVerificationState(rx.State):
    found: bool = False
    loading: bool = False
    error: str = ""
    number: str = ""
    _verification_token: str = ""
    trainee: str = ""
    training: str = ""
    issuer: str = ""
    issued: str = ""
    revoked: bool = False
    competencies: list[dict[str, str]] = []
    qr: str = ""
    verification_url: str = ""

    @rx.event
    async def load(self):
        self.found = False
        self.loading = True
        self.error = ""
        self.qr = ""
        self.competencies = []
        self.number = ""
        self._verification_token = ""
        self.trainee = ""
        self.training = ""
        self.issuer = ""
        self.issued = ""
        self.revoked = False
        self.verification_url = ""
        try:
            number = getattr(self, "certificate_id", "")
            if number is None or number == "":
                path = self.router.url.path
                number = (
                    path.rsplit("/", 1)[-1] if isinstance(path, str) else ""
                )
            if not isinstance(number, str):
                return
            number = unquote(number, errors="strict")
            if (
                not number.strip()
                or len(number) > 64
                or "/" in number
                or "\\" in number
                or any(unicodedata.category(char) == "Cc" for char in number)
            ):
                return
            async with rx.asession() as session:
                row = (
                    await session.execute(
                        text("""SELECT cert.id,cert.certificate_number,u.full_name,c.title,COALESCE(issuer.full_name,'Issuer not recorded'),cert.issued_at,cert.is_revoked
                    FROM cc_certificate cert JOIN cc_user u ON u.id=cert.trainee_id JOIN cc_course c ON c.id=cert.course_id
                    LEFT JOIN cc_user issuer ON issuer.id=cert.issued_by_id WHERE cert.verification_code=:number LIMIT 1"""),
                        {"number": number},
                    )
                ).first()
                if row:
                    competencies = (
                        await session.execute(
                            text("""SELECT c.name,cc.certified_level,e.verification_status,e.verified_at
                        FROM cc_certificate_competency cc JOIN cc_competency c ON c.id=cc.competency_id
                        JOIN cc_competency_evidence e ON e.id=cc.evidence_id AND e.competency_id=cc.competency_id
                        JOIN cc_certificate cert ON cert.id=cc.certificate_id AND cert.trainee_id=e.user_id
                        WHERE cc.certificate_id=:id ORDER BY c.name LIMIT 100"""),
                            {"id": row[0]},
                        )
                    ).all()
                    self._verification_token = number
                    self.number = str(row[1])
                    self.trainee = str(row[2])
                    self.training = str(row[3])
                    self.issuer = str(row[4])
                    self.issued = str(row[5])
                    self.revoked = bool(row[6])
                    self.competencies = [
                        {
                            "name": r[0],
                            "level": str(r[1]),
                            "status": r[2],
                            "verified": str(r[3]) if r[3] else "Not verified",
                        }
                        for r in competencies
                    ]
                    self.found = True
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = "Certificate verification is temporarily unavailable. Please retry."
        finally:
            self.loading = False
        if self.found:
            yield rx.call_script(
                "window.location.origin",
                callback=CertificateVerificationState.make_qr,
            )

    @rx.event
    def make_qr(self, origin: str):
        if not self.found or not self.number:
            return
        try:
            self.verification_url, self.qr = certificate_qr(
                origin, self._verification_token
            )
        except Exception as e:
            logging.exception(f"Error: {type(e).__name__}")
            self.error = (
                "Certificate loaded; the QR code could not be generated."
            )
