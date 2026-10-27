"""Public statements + curator-only answers/hidden fixtures for the starter contest."""

def students(rows):
    return {'tables': [{'name': 'students', 'columns': [['id', 'INTEGER'], ['name', 'TEXT'], ['score', 'INTEGER']], 'rows': rows}]}


def groups(rows):
    return {'tables': [{'name': 'results', 'columns': [['id', 'INTEGER'], ['group_name', 'TEXT'], ['score', 'INTEGER']], 'rows': rows}]}


def attempts(student_rows, attempt_rows):
    return {'tables': [
        {'name': 'students', 'columns': [['id', 'INTEGER'], ['name', 'TEXT']], 'rows': student_rows},
        {'name': 'attempts', 'columns': [['id', 'INTEGER'], ['student_id', 'INTEGER'], ['score', 'INTEGER']], 'rows': attempt_rows},
    ]}


SPECS = [
    {
        'title': 'Рейтинг учеников', 'title_kk': 'Оқушылар рейтингі',
        'statement': '<p>Из таблицы <code>students</code> выберите учеников с <code>score ≥ 35</code>. Выведите столбцы <code>id, name, score</code> именно в этом порядке. Отсортируйте по баллу по убыванию, при равенстве — по <code>id</code> по возрастанию.</p><p><code>id</code> уникален; балл — целое число от 0 до 50 или NULL (результата нет). Строки с NULL не включайте.</p><h3>Результат на открытых данных</h3><pre>id | name  | score\n3  | Дана  | 42\n1  | Алия  | 35\n4  | Алия  | 35</pre>',
        'statement_kk': '<p><code>students</code> кестесінен <code>score ≥ 35</code> оқушыларды таңдаңыз. <code>id, name, score</code> бағандарын дәл осы ретпен шығарыңыз. Ұпайды кему ретімен, тең болса <code>id</code> мәнін өсу ретімен сұрыптаңыз.</p><p><code>id</code> бірегей; ұпай 0–50 аралығында немесе NULL (нәтиже жоқ). NULL жолдарын қоспаңыз.</p><h3>Ашық деректер нәтижесі</h3><pre>id | name  | score\n3  | Дана  | 42\n1  | Алия  | 35\n4  | Алия  | 35</pre>',
        'sql_sample': students([[1,'Алия',35],[2,'Тимур',28],[3,'Дана',42],[4,'Алия',35],[5,'Арман',None]]),
        'sql_reference': 'SELECT id, name, score FROM students WHERE score >= 35 ORDER BY score DESC, id ASC',
        'sql_ordered': True,
        'fixtures': [students([]), students([[1,'A',34],[2,'B',35],[3,'C',36]]), students([[9,'Same',50],[2,'Same',50],[7,'C',35]]), students([[1,'A',None],[2,'B',0],[3,'C',34]]), students([[8,'A',36],[4,'B',49],[6,'C',50],[1,'D',35]]), students([[2,'Q',None],[7,'Z',35]])],
    },
    {
        'title': 'Сильные группы', 'title_kk': 'Үздік топтар',
        'statement': '<p>В <code>results</code> каждая строка — результат попытки. Для каждой группы посчитайте число попыток с ненулевым (не NULL) <code>score</code> и средний балл. Оставьте группы с минимум двумя такими попытками и средним баллом не ниже 30. Отбор выполняйте по среднему <strong>до округления</strong>.</p><p>Выведите <code>group_name, attempts_count, average_score</code> в этом порядке. Средний балл округлите до одного знака функцией <code>ROUND</code>. Сортировка — по <code>group_name</code> по возрастанию. Название группы не NULL; балл 0–50 или NULL. Балл 0 учитывается как обычное число.</p><h3>Результат на открытых данных</h3><pre>group_name | attempts_count | average_score\nA          | 2              | 35.0</pre>',
        'statement_kk': '<p><code>results</code> кестесінің әр жолы — бір талпыныс. Әр топ үшін NULL емес <code>score</code> саны мен орташа ұпайды есептеңіз. Кемінде екі осындай талпынысы бар және орташа ұпайы 30-дан төмен емес топтарды қалдырыңыз. Шартты <strong>дөңгелектеуге дейінгі</strong> орташа мәнге қолданыңыз.</p><p><code>group_name, attempts_count, average_score</code> бағандарын осы ретпен шығарыңыз. Орташа мәнді <code>ROUND</code> арқылы бір ондық таңбаға дөңгелектеңіз. <code>group_name</code> бойынша өсу ретімен сұрыптаңыз. Топ атауы NULL емес; ұпай 0–50 немесе NULL. 0 кәдімгі ұпай ретінде есептеледі.</p><h3>Ашық деректер нәтижесі</h3><pre>group_name | attempts_count | average_score\nA          | 2              | 35.0</pre>',
        'sql_sample': groups([[1,'A',40],[2,'A',30],[3,'A',None],[4,'B',50],[5,'C',20],[6,'C',30]]),
        'sql_reference': 'SELECT group_name, COUNT(score) AS attempts_count, ROUND(AVG(score), 1) AS average_score FROM results GROUP BY group_name HAVING COUNT(score) >= 2 AND AVG(score) >= 30 ORDER BY group_name',
        'sql_ordered': True,
        'fixtures': [groups([]), groups([[1,'A',30],[2,'A',30],[3,'B',None],[4,'B',50]]), groups([[1,'A',0],[2,'A',50],[3,'A',50],[4,'B',None],[5,'B',None]]), groups([[1,'Z',50],[2,'Z',40],[3,'A',30],[4,'A',31],[5,'A',None]]), groups([[1,'A',29],[2,'A',30],[3,'B',30],[4,'B',30]]), groups([[1,'X',30],[2,'X',30],[3,'X',30],[4,'Y',50]])],
    },
    {
        'title': 'Лучший результат каждого', 'title_kk': 'Әр оқушының үздік нәтижесі',
        'statement': '<p>Используя <code>students</code> и <code>attempts</code>, выведите <strong>каждого</strong> ученика и его максимальный балл. Если попыток нет или все их баллы NULL, выведите 0.</p><p>Столбцы: <code>id, name, best_score</code>. Сортировка — по <code>students.id</code> по возрастанию. Идентификаторы уникальны, имена могут повторяться. <code>attempts.student_id</code> ссылается на ученика; балл 0–50 или NULL.</p><h3>Результат на открытых данных</h3><pre>id | name  | best_score\n1  | Алия  | 45\n2  | Тимур | 0\n3  | Дана  | 0</pre>',
        'statement_kk': '<p><code>students</code> және <code>attempts</code> кестелері арқылы <strong>әрбір</strong> оқушыны және оның ең жоғары ұпайын шығарыңыз. Талпынысы болмаса немесе барлық ұпайы NULL болса, 0 шығарыңыз.</p><p>Бағандар: <code>id, name, best_score</code>. <code>students.id</code> бойынша өсу ретімен сұрыптаңыз. Идентификаторлар бірегей, аттар қайталануы мүмкін. <code>attempts.student_id</code> оқушыға сілтейді; ұпай 0–50 немесе NULL.</p><h3>Ашық деректер нәтижесі</h3><pre>id | name  | best_score\n1  | Алия  | 45\n2  | Тимур | 0\n3  | Дана  | 0</pre>',
        'sql_sample': attempts([[1,'Алия'],[2,'Тимур'],[3,'Дана']], [[1,1,30],[2,1,45],[3,3,None]]),
        'sql_reference': 'SELECT s.id, s.name, COALESCE(MAX(a.score), 0) AS best_score FROM students AS s LEFT JOIN attempts AS a ON a.student_id = s.id GROUP BY s.id, s.name ORDER BY s.id',
        'sql_ordered': True,
        'fixtures': [attempts([],[]), attempts([[1,'A'],[2,'B']],[]), attempts([[8,'Same'],[2,'Same']],[[1,8,20],[2,2,50]]), attempts([[1,'A'],[2,'B']],[[1,1,None],[2,1,None],[3,2,0]]), attempts([[7,'A'],[3,'B'],[9,'C']],[[1,7,1],[2,7,50],[3,3,35],[4,7,50]]), attempts([[1,'A'],[2,'B']],[[1,2,49],[2,2,30],[3,1,20]])],
    },
]
