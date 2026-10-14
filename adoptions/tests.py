from unittest.mock import patch
from django.db import transaction
from rest_framework.test import APITestCase
from accounts.models import User
from animals.models import Animal, Species
from shelters.models import Refuge
from notifications.models import Notification
from notifications.services import notify
from .models import AdoptionRequest


class AdoptionFlowTests(APITestCase):
    def setUp(self):
        self.volunteer = User.objects.create_user(username="oussama", first_name="Oussama", email="o@example.test", role=User.Role.BENEVOLE)
        self.citizen = User.objects.create_user(username="citizen", role=User.Role.CITOYEN)
        self.owner = User.objects.create_user(username="refuge", role=User.Role.REFUGE)
        self.other_owner = User.objects.create_user(username="other-refuge", role=User.Role.REFUGE)
        self.admin = User.objects.create_user(username="admin", role=User.Role.ADMIN)
        self.refuge = Refuge.objects.create(user=self.owner, name="Refuge de Tunis", latitude=36.8, longitude=10.2)
        self.other_refuge = Refuge.objects.create(user=self.other_owner, name="Autre refuge", latitude=36.8, longitude=10.3)
        species = Species.objects.create(name="Chien")
        self.animal = Animal.objects.create(name="Milo", species=species, refuge=self.refuge, is_adoptable=True)

    def create_request(self, user=None):
        self.client.force_authenticate(user or self.volunteer)
        result = self.client.post('/api/adoptions/', {"animal": self.animal.pk, "message": "Je souhaite accueillir Milo."}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        return result.data

    def action(self, user, request_id, action):
        self.client.force_authenticate(user)
        return self.client.post(f'/api/adoptions/{request_id}/{action}/', {}, format='json')

    def test_volunteer_creates_request_and_refuge_receives_linked_notification(self):
        data = self.create_request()
        self.assertEqual(data['applicant'], self.volunteer.pk)
        self.assertEqual(data['status'], 'pending')
        self.assertTrue(data['can_cancel'])
        self.assertFalse(data['can_review'])
        self.assertEqual(data['applicant_name'], 'Oussama')
        note = Notification.objects.get(recipient=self.owner)
        self.assertEqual(note.title, 'Nouvelle demande d’adoption')
        self.assertEqual(note.body, 'Oussama souhaite adopter Milo')
        self.assertEqual(note.data['adoption_id'], data['id'])
        self.assertEqual(Notification.objects.count(), 1)

    def test_identity_is_taken_from_authenticated_user(self):
        self.client.force_authenticate(self.volunteer)
        result = self.client.post('/api/adoptions/', {"animal": self.animal.pk, "applicant": self.owner.pk, "refuge": self.other_refuge.pk, "status": "approved"}, format='json')
        self.assertEqual(result.status_code, 201, result.data)
        self.assertEqual(result.data['applicant'], self.volunteer.pk)
        self.assertEqual(result.data['refuge'], self.refuge.pk)
        self.assertEqual(result.data['status'], 'pending')

    def test_duplicate_does_not_create_another_request_or_notification(self):
        self.create_request()
        result = self.client.post('/api/adoptions/', {"animal": self.animal.pk}, format='json')
        self.assertEqual(result.status_code, 400)
        self.assertEqual(AdoptionRequest.objects.count(), 1)
        self.assertEqual(Notification.objects.count(), 1)

    def test_unavailable_animal_and_wrong_role_cannot_apply(self):
        self.animal.is_adoptable = False
        self.animal.save()
        self.client.force_authenticate(self.volunteer)
        self.assertEqual(self.client.post('/api/adoptions/', {"animal": self.animal.pk}, format='json').status_code, 400)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post('/api/adoptions/', {"animal": self.animal.pk}, format='json').status_code, 403)
        self.assertFalse(AdoptionRequest.objects.exists())

    def test_lists_details_and_actions_are_scoped(self):
        data = self.create_request()
        for user in (self.citizen, self.other_owner):
            self.client.force_authenticate(user)
            self.assertEqual(self.client.get('/api/adoptions/').data, [])
            self.assertEqual(self.client.get(f'/api/adoptions/{data["id"]}/').status_code, 404)
            self.assertIn(self.action(user, data['id'], 'approve').status_code, (403, 404))
        self.client.force_authenticate(self.owner)
        received = self.client.get('/api/adoptions/').data
        self.assertEqual(len(received), 1)
        self.assertTrue(received[0]['can_review'])
        self.assertFalse(received[0]['can_cancel'])
        self.assertEqual(received[0]['applicant_email'], 'o@example.test')
        self.assertEqual(self.client.get('/api/adoptions/?animal=invalid').status_code, 400)
        self.assertEqual(self.client.get('/api/adoptions/?animal=999').data, [])

    def test_applicant_cannot_review_even_after_becoming_admin(self):
        data = self.create_request()
        self.assertEqual(self.action(self.volunteer, data['id'], 'approve').status_code, 403)
        self.volunteer.role = User.Role.ADMIN
        self.volunteer.save()
        self.assertEqual(self.action(self.volunteer, data['id'], 'approve').status_code, 403)
        self.assertEqual(self.action(self.volunteer, data['id'], 'reject').status_code, 403)
        detail = self.client.get(f'/api/adoptions/{data["id"]}/').data
        self.assertFalse(detail['can_review'])

    def test_acceptance_updates_animal_rejects_other_pending_and_notifies_every_applicant(self):
        selected = self.create_request()
        other = self.create_request(self.citizen)
        result = self.action(self.owner, selected['id'], 'approve')
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data['status'], 'approved')
        self.assertFalse(result.data['can_review'])
        self.animal.refresh_from_db()
        self.assertFalse(self.animal.is_adoptable)
        self.assertEqual(self.animal.status, Animal.Status.ADOPTED)
        self.assertEqual(AdoptionRequest.objects.get(pk=other['id']).status, 'rejected')
        accepted = Notification.objects.get(recipient=self.volunteer)
        self.assertEqual(accepted.title, 'Demande acceptée')
        self.assertIn('Refuge de Tunis a accepté', accepted.body)
        self.assertEqual(accepted.data['adoption_id'], selected['id'])
        rejected = Notification.objects.get(recipient=self.citizen)
        self.assertEqual(rejected.data['adoption_id'], other['id'])
        self.assertIn('autre candidat', rejected.body)
        count = Notification.objects.count()
        for action in ('approve', 'reject'):
            self.assertEqual(self.action(self.owner, selected['id'], action).status_code, 400)
        self.assertEqual(self.action(self.owner, other['id'], 'approve').status_code, 400)
        self.assertEqual(Notification.objects.count(), count)

    def test_rejection_notifies_applicant_and_preserves_animal_availability(self):
        data = self.create_request()
        result = self.action(self.owner, data['id'], 'reject')
        self.assertEqual(result.data['status'], 'rejected')
        self.assertFalse(result.data['can_review'])
        self.animal.refresh_from_db()
        self.assertTrue(self.animal.is_adoptable)
        note = Notification.objects.get(recipient=self.volunteer)
        self.assertEqual(note.title, 'Demande refusée')
        self.assertIn('Refuge de Tunis a refusé', note.body)

    def test_only_applicant_can_cancel_pending_request_and_reapply(self):
        data = self.create_request()
        self.assertEqual(self.action(self.owner, data['id'], 'cancel').status_code, 403)
        cancelled = self.action(self.volunteer, data['id'], 'cancel')
        self.assertEqual(cancelled.data['status'], 'cancelled')
        self.assertFalse(cancelled.data['can_cancel'])
        self.assertEqual(self.action(self.volunteer, data['id'], 'cancel').status_code, 400)
        self.assertEqual(self.action(self.owner, data['id'], 'approve').status_code, 400)
        new = self.create_request()
        self.assertNotEqual(new['id'], data['id'])
        self.assertEqual(len(self.client.get('/api/adoptions/').data), 2)

    def test_notification_failure_rolls_back_request(self):
        self.client.force_authenticate(self.volunteer)
        with patch('adoptions.services.notify', side_effect=RuntimeError('DB unavailable')):
            with self.assertRaises(RuntimeError):
                self.client.post('/api/adoptions/', {"animal": self.animal.pk}, format='json')
        self.assertFalse(AdoptionRequest.objects.exists())

    def test_notifications_are_broadcast_only_after_commit_and_discarded_on_rollback(self):
        with patch('notifications.services.get_channel_layer') as layer:
            layer.return_value = None
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                self.create_request()
                layer.assert_not_called()
            self.assertEqual(len(callbacks), 1)
            layer.assert_called_once()
            layer.reset_mock()
            with self.captureOnCommitCallbacks(execute=True) as callbacks:
                try:
                    with transaction.atomic():
                        notify(recipient=self.owner, type=Notification.Type.ADOPTION_UPDATE, title='Rollback')
                        raise ValueError('rollback')
                except ValueError:
                    pass
            self.assertEqual(callbacks, [])
            layer.assert_not_called()
            self.assertFalse(Notification.objects.filter(title='Rollback').exists())
