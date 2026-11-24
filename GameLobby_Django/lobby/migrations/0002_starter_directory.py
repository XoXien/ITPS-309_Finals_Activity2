from django.db import migrations


def seed_directory(apps, schema_editor):
    Game = apps.get_model("lobby", "Game")
    Platform = apps.get_model("lobby", "Platform")
    db = schema_editor.connection.alias
    names = ("PC", "Console", "Mobile", "Web", "Tabletop", "Other")
    platforms = {
        name: Platform.objects.using(db).get_or_create(name=name)[0] for name in names
    }
    games = [
        (
            "Minecraft",
            "Sandbox",
            "Build, explore, and share a survival or creative world.",
            ("PC", "Console", "Mobile"),
        ),
        (
            "Mobile Legends: Bang Bang",
            "Team strategy",
            "Find players for five-on-five matches and coordinate your team's roles.",
            ("Mobile",),
        ),
        (
            "Stardew Valley",
            "Farming sim",
            "Meet fellow farmers, plan a co-op farm, or swap tips for the next season.",
            ("PC", "Console", "Mobile"),
        ),
        (
            "Tekken 8",
            "Fighting",
            "Find practice partners and discuss matchups and techniques.",
            ("PC", "Console"),
        ),
        (
            "Valorant",
            "Tactical shooter",
            "Find a squad, coordinate roles, and plan your next match.",
            ("PC", "Console"),
        ),
        (
            "Hollow Knight",
            "Action adventure",
            "Discuss the world of Hallownest, share discoveries, and trade boss strategies.",
            ("PC", "Console"),
        ),
    ]
    for title, genre, description, available in games:
        game, created = Game.objects.using(db).get_or_create(
            title=title, defaults={"genre": genre, "description": description}
        )
        if created:
            game.platforms.set([platforms[n] for n in available])


class Migration(migrations.Migration):
    dependencies = [("lobby", "0001_initial")]
    operations = [migrations.RunPython(seed_directory, migrations.RunPython.noop)]
