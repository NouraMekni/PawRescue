from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from shelters.models import Refuge

User = get_user_model()


class MessagingApiTests(APITestCase):
    def setUp(self):
        self.citizen = User.objects.create_user(
            username="sara",
            email="sara@test.tn",
            password="StrongPass123",
            role=User.Role.CITOYEN,
            first_name="Sara",
        )
        self.refuge_user = User.objects.create_user(
            username="refuge",
            email="refuge@test.tn",
            password="StrongPass123",
            role=User.Role.REFUGE,
            first_name="Refuge",
        )
        self.refuge = Refuge.objects.create(
            user=self.refuge_user,
            name="Refuge Tunis",
            latitude=36.8,
            longitude=10.18,
        )

    def login(self, email):
        response = self.client.post(
            "/api/auth/token/",
            {"email": email, "password": "StrongPass123"},
            format="json",
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access']}")
        return response.data["access"]

    def test_request_must_be_accepted_before_a_reply(self):
        self.login("sara@test.tn")
        created = self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Bonjour, un chien est blessé."},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], "pending")
        conversation_id = created.data["id"]

        reply = self.client.post(
            f"/api/messaging/conversations/{conversation_id}/messages/",
            {"body": "Un autre message"},
            format="json",
        )
        self.assertEqual(reply.status_code, 400)
        self.assertEqual(reply.data["detail"], "En attente d'acceptation.")

        self.login("refuge@test.tn")
        inbox = self.client.get("/api/messaging/conversations/")
        self.assertTrue(inbox.data[0]["needs_response"])
        too_early = self.client.post(
            f"/api/messaging/conversations/{conversation_id}/messages/",
            {"body": "Je réponds"},
            format="json",
        )
        self.assertEqual(too_early.status_code, 400)

        accepted = self.client.post(f"/api/messaging/conversations/{conversation_id}/accept/")
        self.assertEqual(accepted.status_code, 200, accepted.data)
        self.assertEqual(accepted.data["status"], "accepted")

        sent = self.client.post(
            f"/api/messaging/conversations/{conversation_id}/messages/",
            {"body": "Nous arrivons."},
            format="json",
        )
        self.assertEqual(sent.status_code, 201, sent.data)
        self.assertEqual(sent.data["body"], "Nous arrivons.")

    def test_block_stops_a_new_conversation(self):
        self.login("sara@test.tn")
        created = self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Bonjour"},
            format="json",
        )
        conversation_id = created.data["id"]

        self.login("refuge@test.tn")
        blocked = self.client.post(f"/api/messaging/conversations/{conversation_id}/block/")
        self.assertEqual(blocked.status_code, 200, blocked.data)
        self.assertEqual(blocked.data["status"], "blocked")

        self.login("sara@test.tn")
        again = self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Je réessaie"},
            format="json",
        )
        self.assertEqual(again.status_code, 403)
        self.assertEqual(again.data["detail"], "Vous ne pouvez pas envoyer de message.")

    def test_citizen_can_request_a_veterinarian(self):
        vet = User.objects.create_user(
            username="leila",
            email="leila@test.tn",
            password="StrongPass123",
            role=User.Role.VETERINAIRE,
            first_name="Leila",
            last_name="Vet",
            phone="20000000",
        )
        self.login("sara@test.tn")
        listed = self.client.get("/api/messaging/veterinaires/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.data[0]["name"], "Leila Vet")
        self.assertEqual(listed.data[0]["phone"], "20000000")

        created = self.client.post(
            "/api/messaging/conversations/",
            {"veterinaire": vet.id, "body": "Bonjour docteur"},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)
        self.assertEqual(created.data["status"], "pending")
        self.assertEqual(created.data["veterinaire_name"], "Leila Vet")

        self.login("leila@test.tn")
        inbox = self.client.get("/api/messaging/conversations/")
        self.assertEqual(len(inbox.data), 1)
        self.assertTrue(inbox.data[0]["needs_response"])

    def test_inbox_photo_is_the_other_profile(self):
        self.refuge_user.photo = "users/photos/refuge.jpg"
        self.refuge_user.save(update_fields=["photo"])
        self.citizen.photo = "users/photos/sara.jpg"
        self.citizen.save(update_fields=["photo"])
        self.login("sara@test.tn")
        self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Bonjour"},
            format="json",
        )

        citizen_inbox = self.client.get("/api/messaging/conversations/")
        self.assertIn("/media/users/photos/refuge.jpg", citizen_inbox.data[0]["photo"])

        self.login("refuge@test.tn")
        refuge_inbox = self.client.get("/api/messaging/conversations/")
        self.assertIn("/media/users/photos/sara.jpg", refuge_inbox.data[0]["photo"])

    def test_directory_uses_address_and_lists_refuge_accounts(self):
        from accounts.models import VeterinaireProfile

        vet = User.objects.create_user(
            username="leila",
            email="leila@test.tn",
            password="StrongPass123",
            role=User.Role.VETERINAIRE,
            first_name="Leila",
            last_name="Vet",
        )
        VeterinaireProfile.objects.create(
            user=vet,
            address="Dardo, Ariana",
            latitude=36.8,
            longitude=10.1,
        )
        bare = User.objects.create_user(
            username="refuge2",
            email="refuge2@test.tn",
            password="StrongPass123",
            role=User.Role.REFUGE,
            first_name="Refuge",
            last_name="Sidi Bou",
        )
        self.refuge.address = "La Marsa"
        self.refuge.save(update_fields=["address"])

        self.login("sara@test.tn")
        refuges = self.client.get("/api/messaging/refuges/")
        self.assertEqual(refuges.status_code, 200)
        by_name = {row["name"]: row for row in refuges.data}
        self.assertEqual(by_name["Refuge Tunis"]["location"], "La Marsa")
        self.assertEqual(by_name["Refuge Sidi Bou"]["location"], "")
        self.assertTrue(Refuge.objects.filter(user=bare).exists())

        vets = self.client.get("/api/messaging/veterinaires/")
        self.assertEqual(vets.data[0]["location"], "Dardo, Ariana")
        self.assertNotIn("36.8", vets.data[0]["location"])
