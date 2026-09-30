from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase

from shelters.models import Refuge

from .models import Notification

User = get_user_model()


class NotificationApiTests(APITestCase):
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

    def test_a_received_message_notifies_only_the_other_person(self):
        self.login("sara@test.tn")
        created = self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Un chien est blessé."},
            format="json",
        )
        self.assertEqual(created.status_code, 201, created.data)

        self.assertEqual(Notification.objects.filter(recipient=self.citizen).count(), 0)
        note = Notification.objects.get(recipient=self.refuge_user)
        self.assertEqual(note.type, Notification.Type.NEW_MESSAGE)
        self.assertEqual(note.body, "Un chien est blessé.")
        self.assertEqual(note.data["conversation_id"], created.data["id"])

        self.login("refuge@test.tn")
        listed = self.client.get("/api/notifications/")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.data), 1)
        self.assertFalse(listed.data[0]["is_read"])

        read = self.client.post(f"/api/notifications/{note.id}/read/")
        self.assertEqual(read.status_code, 200)
        self.assertTrue(read.data["is_read"])

        self.login("sara@test.tn")
        hidden = self.client.post(f"/api/notifications/{note.id}/read/")
        self.assertEqual(hidden.status_code, 404)

    def test_accept_and_block_notify_the_other_person(self):
        self.login("sara@test.tn")
        created = self.client.post(
            "/api/messaging/conversations/",
            {"refuge": self.refuge.id, "body": "Bonjour"},
            format="json",
        )
        conversation_id = created.data["id"]

        self.login("refuge@test.tn")
        accepted = self.client.post(f"/api/messaging/conversations/{conversation_id}/accept/")
        self.assertEqual(accepted.status_code, 200)

        accepted_note = Notification.objects.get(
            recipient=self.citizen,
            type=Notification.Type.REQUEST_ACCEPTED,
        )
        self.assertEqual(accepted_note.body, "Vous pouvez maintenant échanger des messages.")
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.refuge_user,
                type=Notification.Type.REQUEST_ACCEPTED,
            ).exists()
        )

        blocked = self.client.post(f"/api/messaging/conversations/{conversation_id}/block/")
        self.assertEqual(blocked.status_code, 200)
        blocked_note = Notification.objects.get(
            recipient=self.citizen,
            type=Notification.Type.CONVERSATION_BLOCKED,
        )
        self.assertEqual(blocked_note.data["conversation_id"], conversation_id)
        self.assertFalse(
            Notification.objects.filter(
                recipient=self.refuge_user,
                type=Notification.Type.CONVERSATION_BLOCKED,
            ).exists()
        )
