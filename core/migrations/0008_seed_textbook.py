from django.db import migrations

# Bibliography and paragraph starts visually checked in user-supplied 952.pdf,
# title/imprint pp. 1–2 and complete contents pp. 3–4. No PDF is distributed.
ROWS = [
 ('1.1', 'Ақпаратты өлшеу', 7, ['information', 'measure'], ['03'], 'измерение информации,ақпаратты өлшеу'),
 ('1.2', 'Процессор және оның сипаттамалары', 13, ['hardware'], ['01','08'], 'процессор,processor'),
 ('1.3', 'Компьютерлік желілер', 20, ['networks'], ['02'], 'сети,сеть,желілер,желі'),
 ('2.2', 'Желідегі қауіпсіздік', 36, ['security'], ['02'], 'безопасность,қауіпсіздік'),
 ('3.1', 'Статистикалық мәліметтер', 45, ['spreadsheets'], ['12'], 'статистика,статистикалық'),
 ('3.2', 'Кірістірілген функциялар', 54, ['spreadsheets'], ['12'], 'excel,электронные таблицы,электрондық кестелер'),
 ('3.3', 'Қолжетімді ақпараттың негізінде деректерді талдау', 64, ['spreadsheets'], ['12'], 'анализ данных,деректерді талдау'),
 ('3.4', 'Қолданбалы есептерді шешу', 74, ['spreadsheets'], ['12'], 'прикладные задачи,қолданбалы есептер'),
 ('4.1', 'While циклі', 98, ['python'], ['06'], 'while'),
 ('4.2', 'For циклі', 104, ['python'], ['06'], 'for'),
 ('4.3', 'Break циклін басқару', 111, ['python'], ['06'], 'break'),
 ('4.4', 'Continue циклін басқару', 116, ['python'], ['06'], 'continue'),
 ('4.5', 'Else циклін басқару', 120, ['python'], ['06'], 'else'),
 ('4.6', 'Алгоритмнің трассировкасы', 126, ['algorithms','python'], ['06'], 'трассировка,трассировкасы'),
 ('5.1', 'Мәселені қалыптастыру', 138, ['algorithms'], ['06'], 'постановка задачи,мәселені қалыптастыру'),
 ('5.2', 'Алгоритмді әзірлеу', 144, ['algorithms'], ['06'], 'разработка алгоритма,алгоритмді әзірлеу'),
 ('5.3', 'Алгоритмді программалау', 149, ['algorithms','python'], ['06'], 'программирование алгоритма,алгоритмді программалау'),
 ('5.4', 'Программаны тестілеу', 157, ['python'], ['06'], 'тестирование программы,программаны тестілеу'),
]


def seed(apps, schema_editor):
    db = schema_editor.connection.alias
    Book = apps.get_model('core', 'Textbook')
    Ref = apps.get_model('core', 'TextbookReference')
    Section = apps.get_model('core', 'Section')
    Topic = apps.get_model('core', 'ENTTopic')
    book, _ = Book.objects.using(db).get_or_create(isbn='978-601-331-945-2', defaults=dict(
        title='Информатика', authors='С. Т. Мухамбетжанова, А. С. Тен, Л. Г. Демидова',
        grade=8, language='kk', publisher='Атамұра', year=2021, page_count=176))
    for paragraph, title, page, slugs, codes, keywords in ROWS:
        ref, created = Ref.objects.using(db).get_or_create(textbook=book, paragraph=paragraph, defaults=dict(
            title=title, page_start=page, verified=True, keywords=keywords,
            verification_note='952.pdf: титул и выходные данные с. 1–2; начало параграфа сверено по оглавлению с. 3–4. Полный диапазон страниц не проверен.'))
        if created:
            ref.sections.add(*Section.objects.using(db).filter(slug__in=slugs, parent__isnull=True))
            ref.ent_topics.add(*Topic.objects.using(db).filter(specification__year=2026, specification__subject='informatics', code__in=codes))


class Migration(migrations.Migration):
    dependencies = [('core', '0007_textbook_textbookreference_and_more')]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
