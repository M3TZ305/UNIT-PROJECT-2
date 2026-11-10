from django.db import migrations


def replace_governorate(apps, schema_editor):
    Governorate = apps.get_model('main', 'Governorate')
    old = Governorate.objects.filter(region_key='madinah', slug='khaybar')
    if Governorate.objects.filter(region_key='madinah', slug='mahd-al-dhahab').exists():
        old.delete()
    else:
        old.update(slug='mahd-al-dhahab', name='مهد الذهب', english_name='Mahd al-Dhahab',
                   summary='تلتقي في مهد الذهب ذاكرة التعدين القديم بدروب القوافل والقرى التاريخية.')


def restore_governorate(apps, schema_editor):
    Governorate = apps.get_model('main', 'Governorate')
    if not Governorate.objects.filter(region_key='madinah', slug='khaybar').exists():
        Governorate.objects.filter(region_key='madinah', slug='mahd-al-dhahab').update(
            slug='khaybar', name='خيبر', english_name='Khaybar',
            summary='تجتمع في خيبر ذاكرة الحصون مع بساتين النخيل.')


class Migration(migrations.Migration):
    dependencies = [('main', '0002_governorate')]
    operations = [migrations.RunPython(replace_governorate, restore_governorate)]
