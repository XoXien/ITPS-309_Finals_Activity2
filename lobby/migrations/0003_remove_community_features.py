from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("lobby", "0002_starter_directory")]

    # Drop child tables before their parents, preserving the player table.
    operations = [
        migrations.DeleteModel(name="Reply"),
        migrations.DeleteModel(name="Membership"),
        migrations.DeleteModel(name="SavedGame"),
        migrations.DeleteModel(name="Post"),
        migrations.DeleteModel(name="Game"),
        migrations.DeleteModel(name="Platform"),
    ]
