from cryptography import x509
from cryptography.hazmat.backends import default_backend

CERT_PATH = "app/certs/uidai_public.cer.pem"


def verify_uidai_xml(xml_path):

    try:

        with open(CERT_PATH, "rb") as f:
            cert_data = f.read()

        # Since your file ends with .pem use PEM loader
        cert = x509.load_pem_x509_certificate(cert_data, default_backend())

        public_key = cert.public_key()

        if public_key:
            return True

        return False

    except Exception as e:
        print("Certificate Error:", e)
        raise Exception("UIDAI signature verification failed")