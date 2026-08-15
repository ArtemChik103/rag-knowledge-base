import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

GLOBAL_FONT_NAME = "Arial"
GLOBAL_FONT_BOLD = "Arial-Bold"

def register_cyrillic_font():
    global GLOBAL_FONT_NAME, GLOBAL_FONT_BOLD
    font_candidates = [
        # Windows paths
        ("Arial", r"C:\Windows\Fonts\arial.ttf"),
        ("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"),
        ("Calibri", r"C:\Windows\Fonts\calibri.ttf"),
        ("SegoeUI", r"C:\Windows\Fonts\segoeui.ttf"),
        # Linux / Debian / Ubuntu / Alpine paths
        ("DejaVuSans", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        ("DejaVuSans-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        ("LiberationSans", "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        ("LiberationSans-Bold", "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"),
        ("FreeSans", "/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    ]
    
    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"

    for name, path in font_candidates:
        if os.path.exists(path):
            try:
                if name not in pdfmetrics.getRegisteredFontNames():
                    pdfmetrics.registerFont(TTFont(name, path))
                if not name.endswith("-Bold") and font_name == "Helvetica":
                    font_name = name
                elif name.endswith("-Bold") and font_bold == "Helvetica-Bold":
                    font_bold = name
            except Exception:
                pass

    if font_name == "Helvetica":
        try:
            import matplotlib
            mpl_font = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf', 'DejaVuSans.ttf')
            mpl_font_bold = os.path.join(os.path.dirname(matplotlib.__file__), 'mpl-data', 'fonts', 'ttf', 'DejaVuSans-Bold.ttf')
            if os.path.exists(mpl_font):
                pdfmetrics.registerFont(TTFont("DejaVuSans", mpl_font))
                font_name = "DejaVuSans"
                font_bold = "DejaVuSans"
                if os.path.exists(mpl_font_bold):
                    pdfmetrics.registerFont(TTFont("DejaVuSans-Bold", mpl_font_bold))
                    font_bold = "DejaVuSans-Bold"
        except Exception:
            pass

    GLOBAL_FONT_NAME = font_name
    GLOBAL_FONT_BOLD = font_bold
    return font_name, font_bold


class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        font_to_use = GLOBAL_FONT_NAME if GLOBAL_FONT_NAME in pdfmetrics.getRegisteredFontNames() else "Arial"
        self.setFont(font_to_use, 8)
        self.setFillColor(colors.HexColor("#71717A"))
        
        # Header
        self.drawString(54, 800, "ООО «ТехноИнновации» | Сводный корпоративный регламент и база знаний")
        self.setStrokeColor(colors.HexColor("#E4E4E7"))
        self.setLineWidth(0.5)
        self.line(54, 792, 541, 792)

        # Footer
        self.line(54, 45, 541, 45)
        self.drawString(54, 32, "Конфиденциально • Внутренний нормативный регламент • Версия 3.0 (2026)")
        self.drawRightString(541, 32, f"Стр. {self._pageNumber} из {page_count}")
        self.restoreState()

def generate_company_policy_pdf(output_path: Path | str = "sample_company_policy.pdf") -> Path:
    font_name, font_bold = register_cyrillic_font()
    out_file = Path(output_path).resolve()
    out_file.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(out_file),
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=64,
        bottomMargin=60,
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        "DocTitle",
        parent=styles["Heading1"],
        fontName=font_bold,
        fontSize=16,
        leading=20,
        textColor=colors.HexColor("#09090B"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#52525B"),
        spaceAfter=14,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=font_bold,
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#18181B"),
        spaceBefore=12,
        spaceAfter=6,
    )

    h2_style = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Heading3"],
        fontName=font_bold,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#27272A"),
        spaceBefore=8,
        spaceAfter=4,
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#3F3F46"),
        spaceAfter=5,
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor("#3F3F46"),
        leftIndent=12,
        firstLineIndent=-8,
        spaceAfter=3,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=font_bold,
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#09090B"),
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#27272A"),
    )

    story = []

    # Title Block
    story.append(Paragraph("СВОДНЫЙ КОРПОРАТИВНЫЙ РЕГЛАМЕНТ, ПРАВИЛА ВНУТРЕННЕГО ТРУДОВОГО РАСПОРЯДКА И ПОЛИТИКИ БЕЗОПАСНОСТИ", title_style))
    story.append(Paragraph("ООО «ТехноИнновации» • Утвержден приказом Генерального директора № 142/ОД от 15 января 2026 г. • Редакция 3.0", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D4D4D8"), spaceAfter=10))

    # SECTION 1
    story.append(Paragraph("Раздел 1. Общие положения, термины и принципы компании", h1_style))
    story.append(Paragraph("1.1. Настоящий Регламент является локальным нормативным актом ООО «ТехноИнновации» (далее — «Компания») и регулирует трудовые отношения, права и обязанности сотрудников, порядок организации рабочих процессов, политики информационной безопасности, компенсации и социальные гарантии.", body_style))
    story.append(Paragraph("1.2. Действие настоящего регламента распространяется на всех штатных сотрудников, стажеров, совместителей и работников на дистанционном режиме с момента подписания трудового договора.", body_style))
    story.append(Paragraph("1.3. Основные ценности Компании: открытость информации, ответственность за результат, инженерное качество, взаимное уважение и соблюдение требований кибербезопасности.", body_style))

    # SECTION 2
    story.append(Paragraph("Раздел 2. График работы, гибкие часы и сверхурочная работа", h1_style))
    story.append(Paragraph("2.1. Базовый режим: В Компании установлена 40-часовая пятидневная рабочая неделя (понедельник–пятница) с двумя выходными днями (суббота и воскресенье).", body_style))
    story.append(Paragraph("2.2. Время работы: Стандартный рабочий день длится с 09:00 до 18:00 (в пятницу — сокращенный день до 17:00). Обеденный перерыв составляет ровно 60 минут в окне с 13:00 до 14:00. Обеденное время не оплачивается и не включается в рабочее время.", body_style))
    story.append(Paragraph("2.3. Гибкий график: Сотрудники IT-подразделений, аналитики и дизайнеры имеют право сдвигать начало рабочего дня в промежутке от 08:00 до 11:00 по согласованию с тимлидом при сохранении 8-часового рабочего дня.", body_style))
    story.append(Paragraph("2.4. Сверхурочная работа: Привлечение к работе сверх установленной продолжительности допускается только с письменного согласия сотрудника и оплачивается: первые 2 часа — в полуторном размере (1.5x), последующие часы и работа в выходные дни — в двойном размере (2.0x).", body_style))
    story.append(Paragraph("2.5. Учет опозданий: Обо всех задержках более чем на 15 минут сотрудник обязан уведомить руководителя и дежурного HR в корпоративном чате Slack (#attendance) не позднее 09:30 утра.", body_style))

    story.append(PageBreak())

    # SECTION 3
    story.append(Paragraph("Раздел 3. Удаленный, гибридный и разъездной формат работы", h1_style))
    story.append(Paragraph("3.1. Категории форматов работы: В Компании предусмотрены три формата: Офисный (5 дней в офисе), Гибридный (от 1 до 3 дней удаленно в неделю) и Полностью удаленный (Full Remote).", body_style))
    story.append(Paragraph("3.2. Условия перехода на удаленный режим: Право на гибридный или удаленный формат предоставляется сотрудникам после успешного прохождения 3 месяцев испытательного срока.", body_style))
    story.append(Paragraph("3.3. Регламент подачи заявки: Заявка на удаленный день оформляется во внутренней системе Jira Service Desk (проект HR-REMOTE) не менее чем за 2 рабочих дня до планируемой даты.", body_style))
    story.append(Paragraph("3.4. Требования к домашнему рабочему месту и сетевой инфраструктуре:", h2_style))
    story.append(Paragraph("• Скорость интернет-соединения: не менее 50 Мбит/с на входящий и исходящий трафик.", bullet_style))
    story.append(Paragraph("• Сетевая безопасность: обязательное использование корпоративного VPN-клиента (WireGuard с обязательной двухфакторной аутентификацией 2FA) при любом подключении к корпоративным серверам, базам данных и Git-репозиториям.", bullet_style))
    story.append(Paragraph("• Рабочие часы доступности: сотрудник обязан находиться на связи в корпоративных мессенджерах и по электронной почте с 10:00 до 19:00 по московскому времени.", bullet_style))
    story.append(Paragraph("• Запрет работы из незащищенных сетей: категорически запрещено выполнять служебные обязанности в общедоступных сетях Wi-Fi (кафе, аэропорты, отели) без включенного VPN и шифрования трафика.", bullet_style))
    story.append(Paragraph("• Работа из-за рубежа: временное выполнение работы за пределами РФ допускается на срок до 90 календарных дней в году при согласовании с директором по безопасности и налоговым отделом.", body_style))

    story.append(Spacer(1, 8))

    # SECTION 4
    story.append(Paragraph("Раздел 4. Информационная безопасность, пароли и защита коммерческой тайны", h1_style))
    story.append(Paragraph("4.1. Парольная политика и учетные записи:", h2_style))
    story.append(Paragraph("• Длина пароля: минимальная длина мастер-пароля составляет 12 символов.", bullet_style))
    story.append(Paragraph("• Сложность: пароль обязан содержать прописные и строчные латинские буквы, минимум 2 цифры и минимум 1 специальный символ (!@#$%^&*).", bullet_style))
    story.append(Paragraph("• Срок ротации: система автоматически запрашивает смену пароля каждые 90 календарных дней. Запрещено повторное использование последних 5 паролей.", bullet_style))
    story.append(Paragraph("• Блокировка: при 5 неверных попытках ввода пароля учетная запись Active Directory блокируется на 30 минут с отправкой алерта в SOC (Security Operations Center).", bullet_style))
    story.append(Paragraph("4.2. Использование съемных накопителей (USB и внешние диски): Запрещено подключение любых неавторизованных USB-накопителей, SD-карт и мобильных телефонов в режиме накопителя. На всех корпоративных ПК действует система DLP (Data Loss Prevention), блокирующая запись на внешние устройства.", body_style))
    story.append(Paragraph("4.3. Обработка конфиденциальной информации и исходного кода: Запрещено копировать, пересылать или публиковать конфиденциальные документы Компании, клиентские базы данных, исходный код и финансовую отчетность через сторонние мессенджеры (Telegram, WhatsApp) или личную почту (@gmail.com, @mail.ru, @yandex.ru).", body_style))
    story.append(Paragraph("4.4. Политика «Чистого стола» и блокировка экрана: При покидании рабочего места сотрудник обязан заблокировать экран комбинацией клавиш Win + L (Cmd + Ctrl + Q для macOS). Не допускается оставлять на столе документы с грифом «Коммерческая тайна».", body_style))

    story.append(PageBreak())

    # SECTION 5
    story.append(Paragraph("Раздел 5. Использование корпоративного оборудования, ноутбуков и ПО", h1_style))
    story.append(Paragraph("5.1. Выдача техники: Каждому сотруднику при выходе на работу предоставляется ноутбук корпоративного стандарта (MacBook Pro / ThinkPad), гарнитура, зарядные устройства и авторизованный токен безопасности 2FA.", body_style))
    story.append(Paragraph("5.2. Установка программного обеспечения: Установка стороннего нелицензионного ПО, торрент-клиентов, криптомайнеров и компьютерных игр на рабочие станции строго запрещена. Запросы на установку платного ПО формируются через портал Helpdesk.", body_style))
    story.append(Paragraph("5.3. Возврат оборудования: При увольнении или замене техники сотрудник обязан сдать оборудование в отдел IT-инфраструктуры в полной комплектации и рабочем состоянии в последний рабочий день.", body_style))

    story.append(Spacer(1, 8))

    # SECTION 6
    story.append(Paragraph("Раздел 6. Оплата труда, структура заработной платы и премирование", h1_style))
    story.append(Paragraph("6.1. Дни выплаты заработной платы: Заработная плата выплачивается 2 раза в месяц в безналичном порядке на банковскую карту сотрудника: аванс — 20-го числа текущего месяца (40% от оклада), окончательный расчет — 5-го числа следующего месяца (60% от оклада).", body_style))
    story.append(Paragraph("6.2. Квартальные премии (KPI): По результатам выполнения квартальных ключевых показателей сотрудникам выплачивается квартальная премия в размере до 30% от квартального фонда оплаты труда на основании решения руководителя подразделения.", body_style))
    story.append(Paragraph("6.3. Ежегодный пересмотр заработных плат (Performance Review): Оценка результативности и пересмотр уровня оплаты труда проводятся ежегодно в ноябре–декабре с вступлением новых условий в силу с 1 января.", body_style))

    story.append(Spacer(1, 8))

    # SECTION 7
    story.append(Paragraph("Раздел 7. Социальный пакет, ДМС, спорт и корпоративные компенсации", h1_style))
    story.append(Paragraph("7.1. Добровольное медицинское страхование (ДМС): Программа ДМС оформляется для сотрудника за счет Компании после прохождения 3 месяцев испытательного срока. Полис включает поликлиническое обслуживание, вызов врача на дом, экстренную госпитализацию и стоматологию.", body_style))
    story.append(Paragraph("7.2. Компенсация спорта и фитнеса: Компания возмещает расходы на абонементы в спортзалы, фитнес-клубы, бассейны и секции в размере до 35 000 рублей в год на одного сотрудника. Выплата производится раз в полгода на основании чеков и договора.", body_style))
    story.append(Paragraph("7.3. Компенсация питания: Сотрудникам офиса предоставляется ежемесячная дотация на питание в корпоративной столовой и кафе-партнерах в размере 6 000 рублей в месяц через карту питания.", body_style))
    story.append(Paragraph("7.4. Корпоративная мобильная связь: Сотрудникам, чьи обязанности связаны с регулярными внешними коммуникациями, предоставляется корпоративная SIM-карта с безлимитным интернетом и пакетом 2000 минут.", body_style))

    story.append(PageBreak())

    # SECTION 8
    story.append(Paragraph("Раздел 8. Профессиональное развитие, обучение и сертификация", h1_style))
    story.append(Paragraph("8.1. Бюджет на обучение: Каждому штатному сотруднику после 6 месяцев работы выделяется ежегодный бюджет на профессиональное обучение в размере до 80 000 рублей. Средства могут быть направлены на курсы, участие в конференциях и покупку литературы.", body_style))
    story.append(Paragraph("8.2. Оплата профессиональной сертификации: Компания на 100% компенсирует стоимость сдачи международных и отраслевых сертификационных экзаменов (AWS, GCP, CISA, PMP, Kubernetes CKA) при условии успешной сдачи экзамена.", body_style))
    story.append(Paragraph("8.3. Изучение английского языка: Всем сотрудникам уровня Middle и выше предоставляется бесплатный доступ к онлайн-платформе корпоративного изучения английского языка с индивидуальными занятиями с преподавателем 2 раза в неделю.", body_style))

    story.append(Spacer(1, 8))

    # TABLE: Complete Benefits Matrix
    story.append(Paragraph("Сводная таблица льгот, лимитов и компенсаций:", h2_style))
    table_data = [
        [
            Paragraph("Льгота / Компенсация", table_header_style),
            Paragraph("Годовой лимит", table_header_style),
            Paragraph("Срок доступности", table_header_style),
            Paragraph("Необходимые документы", table_header_style),
        ],
        [
            Paragraph("Полис ДМС + Стоматология", table_cell_style),
            Paragraph("100% покрытие", table_cell_style),
            Paragraph("После 3 мес. работы", table_cell_style),
            Paragraph("Заявление в HR-портале", table_cell_style),
        ],
        [
            Paragraph("Спорт и фитнес", table_cell_style),
            Paragraph("До 35 000 руб./год", table_cell_style),
            Paragraph("С первого месяца", table_cell_style),
            Paragraph("Договор, чек об оплате", table_cell_style),
        ],
        [
            Paragraph("Обучение и конференции", table_cell_style),
            Paragraph("До 80 000 руб./год", table_cell_style),
            Paragraph("После 6 мес. работы", table_cell_style),
            Paragraph("План развития, счет", table_cell_style),
        ],
        [
            Paragraph("Питание в офисе", table_cell_style),
            Paragraph("72 000 руб./год (6к/мес)", table_cell_style),
            Paragraph("С первого месяца", table_cell_style),
            Paragraph("Автоматически на бейдж", table_cell_style),
        ],
        [
            Paragraph("Английский язык", table_cell_style),
            Paragraph("Бесплатно без лимита", table_cell_style),
            Paragraph("После 3 мес. работы", table_cell_style),
            Paragraph("Тестирование уровня", table_cell_style),
        ],
        [
            Paragraph("Обустройство рабочего места", table_cell_style),
            Paragraph("До 25 000 руб. (разово)", table_cell_style),
            Paragraph("Для Full Remote", table_cell_style),
            Paragraph("Чеки на кресло/монитор", table_cell_style),
        ]
    ]

    t = Table(table_data, colWidths=[130, 115, 115, 127])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F4F4F5")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 4.5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4.5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)

    story.append(PageBreak())

    # SECTION 9
    story.append(Paragraph("Раздел 9. Отпуска, больничные листы и дни Day-off", h1_style))
    story.append(Paragraph("9.1. Основной оплачиваемый отпуск: Составляет 28 календарных дней за каждый рабочий год. Отпуск может делиться на части, при этом продолжительность хотя бы одной из частей должна составлять не менее 14 календарных дней непрерывно.", body_style))
    story.append(Paragraph("9.2. График отпусков: Формируется и утверждается ежегодно до 1 декабря на предстоящий календарный год. Перенос отпуска возможен по согласованию с тимлидом не позднее чем за 14 дней до утвержденной даты.", body_style))
    story.append(Paragraph("9.3. Оформление больничных листов: При наступлении временной нетрудоспособности сотрудник обязан проинформировать руководителя до 10:00 утра первого дня болезни. Номер электронного листка нетрудоспособности (ЭЛН) направляется в бухгалтерию не позднее 3 дней после закрытия.", body_style))
    story.append(Paragraph("9.4. Программа дополнительных дней отдыха (Day-off): Компания предоставляет каждому сотруднику до 3 оплачиваемых дней в календарном году без необходимости оформления больничного листа в случае внезапного легкого недомогания или экстренных семейных обстоятельств.", body_style))

    story.append(Spacer(1, 8))

    # SECTION 10
    story.append(Paragraph("Раздел 10. Служебные командировки и авансовые отчеты", h1_style))
    story.append(Paragraph("10.1. Направление в командировку: Оформляется служебным заданием и приказом за подписью директора. Все расходы на проезд, проживание и суточные покрываются Компанией в полном объеме.", body_style))
    story.append(Paragraph("10.2. Размер суточных: По территории РФ — 2 500 рублей в сутки; для заграничных командировок — 70 долларов США / евро в сутки по курсу ЦБ РФ.", body_style))
    story.append(Paragraph("10.3. Проживание и транспорт: Бронирование гостиниц осуществляется по стандарту до 6 500 рублей в сутки в регионах и до 9 000 рублей в Москве и Санкт-Петербурге. Авиаперелеты бронируются эконом-классом, ж/д поездки — купе.", body_style))
    story.append(Paragraph("10.4. Сроки предоставления авансового отчета: В течение 3 рабочих дней после возвращения из командировки сотрудник обязан предоставить в бухгалтерию авансовый отчет с оригиналами посадочных талонов, чеков и счетов из гостиницы.", body_style))

    story.append(Spacer(1, 8))

    # SECTION 11
    story.append(Paragraph("Раздел 11. Корпоративная этика, дресс-код и урегулирование споров", h1_style))
    story.append(Paragraph("11.1. Стиль одежды (дресс-код): В Компании принят свободный стиль одежды (Smart Casual / Casual). При проведении очных официальных встреч с клиентами и инвесторами рекомендуется деловой стиль (Business Casual).", body_style))
    story.append(Paragraph("11.2. Недискриминация и инклюзивность: В Компании строго запрещены любые формы дискриминации по признакам пола, возраста, национальности, вероисповедания или убеждений. Все сотрудники имеют равные возможности карьерного роста.", body_style))
    story.append(Paragraph("11.3. Разрешение конфликтных ситуаций: Любой рабочий конфликт подлежит первоначальному обсуждению с непосредственным руководителем. При невозможности урегулирования привлекается HR Business Partner или служба медиации.", body_style))

    story.append(PageBreak())

    # SECTION 12
    story.append(Paragraph("Раздел 12. Охрана труда, пожарная безопасность и действия в ЧС", h1_style))
    story.append(Paragraph("12.1. Вводный инструктаж: Каждый сотрудник при приеме на работу проходит обязательный вводный инструктаж по охране труда и пожарной безопасности под роспись в журнале учета.", body_style))
    story.append(Paragraph("12.2. Пожарная безопасность: Курение (включая электронные сигареты и вейпы) на территории офиса категорически запрещено и разрешается только в специально оборудованных уличных зонах. В случае срабатывания пожарной сигнализации сотрудники обязаны немедленно покинуть здание по эвакуационным лестницам.", body_style))
    story.append(Paragraph("12.3. Медицинская аптечка: Аптечки первой помощи расположены на каждом этаже офиса возле кухонных зон и на ресепшн (кабинеты 201, 301, 401).", body_style))

    story.append(Spacer(1, 8))

    # SECTION 13
    story.append(Paragraph("Раздел 13. Контактная информация подразделений и матрица эскалации", h1_style))
    story.append(Paragraph("• Отдел подбора и адаптации персонала: hr@technoinnovations.ru | Внутренний номер: 101 | Кабинет 304", bullet_style))
    story.append(Paragraph("• HR Business Partner: hrbp@technoinnovations.ru | Внутренний номер: 102 | Кабинет 305", bullet_style))
    story.append(Paragraph("• Служба информационной безопасности (SOC): sec@technoinnovations.ru | Круглосуточный телефон: 112 / +7 (495) 100-01-12", bullet_style))
    story.append(Paragraph("• Бухгалтерия и расчетный отдел: payroll@technoinnovations.ru | Внутренний номер: 105 | Кабинет 208", bullet_style))
    story.append(Paragraph("• Служба технической поддержки (Helpdesk): support@technoinnovations.ru | Портал: https://helpdesk.technoinnovations.corp", bullet_style))
    story.append(Paragraph("• Административно-хозяйственный отдел (АХО): facility@technoinnovations.ru | Внутренний номер: 110", bullet_style))
    story.append(Paragraph("• Горячая линия комплаенс и этики: ethics@technoinnovations.ru | Анонимный ящик доверия на 1 этаже", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return out_file

if __name__ == "__main__":
    generated_path = generate_company_policy_pdf()
    print(f"Sample PDF generated successfully: {generated_path}")
