from django.db import migrations

"""Frozen ENT-2026 catalogue and conservative root-section matching."""
import unicodedata

SOURCE_RU = "https://testcenter.kz/upload/iblock/994/15_.pdf"
SOURCE_KK = "https://new.testcenter.kz/wp-content/uploads/2025/10/28_Информатика_каз.pdf"
TOPICS = [('Устройства компьютера', 'Компьютердің құрылғылары', ['hardware']), ('Компьютерные сети. Организация компьютерных сетей. Информационная безопасность', 'Компьютерлік желілер. Компьютерлік желілерді ұйымдастыру. Ақпараттық қауіпсіздік', ['networks', 'security']), ('Представление и измерение информации. Кодирование информации', 'Ақпаратты ұсыну және өлшеу. Ақпаратты кодтау', ['information', 'measure', 'encoding']), ('Системы счисления', 'Есептеу жүйелері', ['numbers']), ('Логические основы компьютера', 'Компьютердің логикалық негіздері', ['logic']), ('Программирование алгоритмов на языке программирования Python', 'Python программалау тілінде алгоритмдерді программалау', ['algorithms', 'python']), ('Алгоритмы и программирование (Функция, Рекурсия, работа со строками, работа с файлами, сортировка, графы)', 'Алгоритмдер және программалау (Функция, Рекурсия, жолдармен жұмыс, файлдармен жұмыс, сұрыптау, граф)', ['python', 'datastructs']), ('Аппаратное обеспечение. Программное обеспечение', 'Аппараттық қамтамасыз ету. Программалық қамтамасыз ету', ['hardware', 'software']), ('Реляционные базы данных', 'Реляциондық деректер қоры', ['sql']), ('Создание базы данных. Структурированные запросы', 'Мәліметтер қорын жасау. Құрылымдалған сұраныстар', ['sql']), ('Современные тенденции развития информационных технологий. IT Startup (ай-ти стартап). 3D проектирование', 'Ақпараттық технологияларды дамытудағы қазіргі заманғы үрдістер. IT Startup (ай-ти стартап) 3D жобалау', []), ('Создание и преобразование информационных объектов', 'Ақпараттық объектілерді құру және түрлендіру', ['spreadsheets']), ('Web-проектирование', 'Web-жобалау', ['web'])]


def normalize(value):
    return " ".join(unicodedata.normalize("NFKC", value).casefold().replace("ё", "е").split())


def seed(apps, schema_editor, map_existing=False):
    Specification = apps.get_model("core", "ENTSpecification")
    Topic = apps.get_model("core", "ENTTopic")
    Section = apps.get_model("core", "Section")
    db = schema_editor.connection.alias
    spec, _ = Specification.objects.using(db).get_or_create(
        year=2026, subject="informatics", defaults={
            "title": "ЕНТ · Информатика", "title_kk": "ҰБТ · Информатика",
            "source_url": SOURCE_RU, "source_url_kk": SOURCE_KK,
            "question_count": 40, "max_score": 50,
        },
    )
    roots = list(Section.objects.using(db).filter(parent__isnull=True))
    for number, (title, title_kk, slugs) in enumerate(TOPICS, 1):
        notes = {
            7: "Частичное покрытие: проверить рекурсию, файлы, сортировку и графы.",
            11: "В исходном курсе нет подходящей корневой темы.",
            12: "Частичное покрытие: электронные таблицы; проверить остальные информационные объекты.",
        }.get(number, "Начальное сопоставление; содержание необходимо проверить вручную.")
        topic, created = Topic.objects.using(db).get_or_create(
            specification=spec, code=f"{number:02}",
            defaults={"title": title, "title_kk": title_kk, "mapping_notes": notes},
        )
        # Do not restore mappings deliberately removed by an administrator.
        if not created and not map_existing:
            continue
        from_titles = ALIASES
        for slug in slugs:
            matches = [s for s in roots if s.slug == slug]
            if not matches:
                names = {normalize(n) for n in from_titles.get(slug, [])}
                matches = [s for s in roots if normalize(s.title) in names or normalize(s.title_kk) in names]
            if len(matches) == 1:
                topic.sections.add(matches[0])

ALIASES = {'information': ['Информация и информационные процессы'], 'numbers': ['Системы счисления'], 'encoding': ['Кодирование информации'], 'measure': ['Измерение информации'], 'logic': ['Основы логики'], 'algorithms': ['Алгоритмы'], 'python': ['Основы Python'], 'datastructs': ['Списки, строки и массивы'], 'cpp': ['Основы C++'], 'sql': ['Базы данных и SQL'], 'spreadsheets': ['Электронные таблицы'], 'hardware': ['Устройство компьютера'], 'software': ['ОС и программное обеспечение'], 'networks': ['Компьютерные сети и интернет'], 'security': ['Информационная безопасность'], 'web': ['Веб-технологии: HTML и CSS']}


class Migration(migrations.Migration):
    dependencies = [("core", "0004_entspecification_enttopic_and_more")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
