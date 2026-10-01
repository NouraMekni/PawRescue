from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0003_veterinaireprofile_address_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="user",
            name="photo",
            field=models.ImageField(blank=True, null=True, upload_to="users/photos/"),
        ),
    ]
