from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APITestCase

from accounts.models import VeterinaireProfile
from animals.models import Species

User = get_user_model()


class AuthApiTests(APITestCase):
    def test_register_citoyen_is_soft_and_returns_token(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "citoyen@example.com", "password": "StrongPass123", "role": "citoyen"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["user"]["role"], "citoyen")
        self.assertEqual(response.data["user"]["profile"], {"address": ""})
        self.assertIn("access", response.data)

    def test_register_admin_is_rejected(self):
        response = self.client.post(
            "/api/auth/register/",
            {"email": "admin@example.com", "password": "StrongPass123", "role": "admin"},
            format="json",
        )
        self.assertEqual(response.status_code, 400)

    def test_pending_vet_cannot_login_until_approved(self):
        document = SimpleUploadedFile("ordre.pdf", b"%PDF-1.4", content_type="application/pdf")
        created = self.client.post(
            "/api/auth/register/",
            {
                "email": "vet@example.com",
                "password": "StrongPass123",
                "role": "veterinaire",
                "first_name": "Leila",
                "last_name": "Vet",
                "phone": "+21698765432",
                "license_number": "4582",
                "governorate": "Tunis",
                "clinic_name": "Clinique VetCare",
                "address": "Avenue Habib Bourguiba",
                "verification_document": document,
            },
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertNotIn("access", created.data)
        self.assertEqual(
            created.data["user"]["profile"]["verification_status"],
            "pending",
        )

        blocked = self.client.post(
            "/api/auth/token/",
            {"email": "vet@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)

        profile = VeterinaireProfile.objects.get(user__email="vet@example.com")
        profile.verification_status = VeterinaireProfile.VerificationStatus.APPROVED
        profile.save(update_fields=["verification_status"])

        login = self.client.post(
            "/api/auth/token/",
            {"email": "vet@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIsNotNone(User.objects.get(email="vet@example.com").last_login)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {login.data['access']}")

        me = self.client.patch(
            "/api/auth/me/",
            {"phone": "20000000", "profile": {"license_number": "VET-1", "radius_km": 25}},
            format="json",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["phone"], "20000000")
        self.assertEqual(me.data["profile"]["license_number"], "VET-1")
        self.assertEqual(me.data["profile"]["radius_km"], 25)

    def test_refuge_profile_is_created_from_me(self):
        user = User.objects.create_user(
            username="refuge",
            email="refuge@example.com",
            password="StrongPass123",
            role=User.Role.REFUGE,
        )
        self.client.force_authenticate(user=user)

        species = Species.objects.create(name="Chien")
        me = self.client.patch(
            "/api/auth/me/",
            {
                "profile": {
                    "name": "Refuge Tunis",
                    "latitude": 36.8,
                    "longitude": 10.18,
                    "accepted_species": [species.id],
                }
            },
            format="json",
        )
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.data["profile"]["name"], "Refuge Tunis")
        self.assertEqual(me.data["profile"]["accepted_species"], [species.id])
        self.assertTrue(User.objects.get(email="refuge@example.com").refuge)

    def test_pending_refuge_cannot_login_until_verified(self):
        document = SimpleUploadedFile("rne.pdf", b"%PDF-1.4", content_type="application/pdf")
        created = self.client.post(
            "/api/auth/register/",
            {
                "email": "shelter@example.com",
                "password": "StrongPass123",
                "role": "refuge",
                "first_name": "Nadia",
                "last_name": "Refuge",
                "phone": "+21698765432",
                "name": "Refuge Tunis",
                "structure": "Refuge",
                "rne": "1234567A",
                "governorate": "Tunis",
                "address": "Avenue Habib Bourguiba",
                "official_email": "contact@refuge.tn",
                "representative_name": "Nadia Ben Ali",
                "verification_document": document,
            },
            format="multipart",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertNotIn("access", created.data)
        self.assertEqual(created.data["user"]["profile"]["verification_status"], "pending")

        blocked = self.client.post(
            "/api/auth/token/",
            {"email": "shelter@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(blocked.status_code, 400)

        refuge = User.objects.get(email="shelter@example.com").refuge
        refuge.is_verified = True
        refuge.save(update_fields=["is_verified"])

        login = self.client.post(
            "/api/auth/token/",
            {"email": "shelter@example.com", "password": "StrongPass123"},
            format="json",
        )
        self.assertEqual(login.status_code, 200)
        self.assertIn("access", login.data)

    def test_citoyen_can_complete_profile_and_photo(self):
        register = self.client.post(
            "/api/auth/register/",
            {
                "email": "sara@example.com",
                "password": "StrongPass123",
                "role": "citoyen",
                "first_name": "Sara",
                "last_name": "Ben Ali",
            },
            format="json",
        )
        self.assertEqual(register.data["user"]["first_name"], "Sara")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {register.data['access']}")

        updated = self.client.patch(
            "/api/auth/me/",
            {
                "phone": "+21620000000",
                "profile": {"address": "Tunis centre"},
            },
            format="json",
        )
        self.assertEqual(updated.status_code, 200, updated.data)
        self.assertEqual(updated.data["phone"], "+21620000000")
        self.assertEqual(updated.data["profile"]["address"], "Tunis centre")

        buffer = BytesIO()
        Image.new("RGB", (8, 8), "green").save(buffer, format="JPEG")
        photo = SimpleUploadedFile("face.jpg", buffer.getvalue(), content_type="image/jpeg")
        with_photo = self.client.patch(
            "/api/auth/me/",
            {"photo": photo},
            format="multipart",
        )
        self.assertEqual(with_photo.status_code, 200, with_photo.data)
        self.assertIn("users/photos/", with_photo.data["photo"])
