import os
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

def register_cyrillic_font():
    # Try Windows standard fonts
    font_candidates = [
        ("Arial", r"C:\Windows\Fonts\arial.ttf"),
        ("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"),
        ("Calibri", r"C:\Windows\Fonts\calibri.ttf"),
        ("SegoeUI", r"C:\Windows\Fonts\segoeui.ttf"),
    ]
    
    font_name = "Helvetica"
    font_bold = "Helvetica-Bold"

    for name, path in font_candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                if name == "Arial":
                    font_name = "Arial"
                elif name == "Arial-Bold":
                    font_bold = "Arial-Bold"
            except Exception:
                pass

    if font_name != "Arial":
        # Check DejaVu or other system fonts
        for win_font in ["DejaVuSans.ttf", "arial.ttf"]:
            full_path = os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "Fonts", win_font)
            if os.path.exists(full_path):
                try:
                    pdfmetrics.registerFont(TTFont("CustomCyrillic", full_path))
                    font_name = "CustomCyrillic"
                    font_bold = "CustomCyrillic"
                    break
                except Exception:
                    pass

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
        self.setFont("Helvetica", 9)
        self.setFillColor(colors.HexColor("#71717A"))
        
        # Header
        self.drawString(54, 800, "ООО «ТехноИнновации» | Регламент трудового распорядка и ИБ")
        self.setStrokeColor(colors.HexColor("#E4E4E7"))
        self.setLineWidth(0.5)
        self.line(54, 792, 541, 792)

        # Footer
        self.line(54, 45, 541, 45)
        self.drawString(54, 32, "Конфиденциально • Внутренний нормативный документ • Версия 2.4")
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
        fontName=font_bold if font_bold in pdfmetrics.getRegisteredFontNames() else font_name,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#09090B"),
        alignment=0, # Left aligned
        spaceAfter=12,
    )

    subtitle_style = ParagraphStyle(
        "DocSubTitle",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#52525B"),
        spaceAfter=18,
    )

    h1_style = ParagraphStyle(
        "SectionHeading",
        parent=styles["Heading2"],
        fontName=font_bold if font_bold in pdfmetrics.getRegisteredFontNames() else font_name,
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#18181B"),
        spaceBefore=14,
        spaceAfter=8,
    )

    h2_style = ParagraphStyle(
        "SubSectionHeading",
        parent=styles["Heading3"],
        fontName=font_bold if font_bold in pdfmetrics.getRegisteredFontNames() else font_name,
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#27272A"),
        spaceBefore=10,
        spaceAfter=6,
    )

    body_style = ParagraphStyle(
        "DocBody",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#3F3F46"),
        spaceAfter=6,
    )

    bullet_style = ParagraphStyle(
        "DocBullet",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#3F3F46"),
        leftIndent=14,
        firstLineIndent=-10,
        spaceAfter=4,
    )

    table_header_style = ParagraphStyle(
        "TableHeader",
        parent=styles["Normal"],
        fontName=font_bold if font_bold in pdfmetrics.getRegisteredFontNames() else font_name,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#09090B"),
    )

    table_cell_style = ParagraphStyle(
        "TableCell",
        parent=styles["Normal"],
        fontName=font_name,
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#27272A"),
    )

    story = []

    # Title Block
    story.append(Paragraph("РЕГЛАМЕНТ ВНУТРЕННЕГО ТРУДОВОГО РАСПОРЯДКА, ИНФОРМАЦИОННОЙ БЕЗОПАСНОСТИ И СОЦИАЛЬНЫХ ГАРАНТИЙ", title_style))
    story.append(Paragraph("ООО «ТехноИнновации» • Утвержден приказом Генерального директора № 142/ОД от 15 января 2026 г.", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#D4D4D8"), spaceAfter=14))

    # SECTION 1
    story.append(Paragraph("Раздел 1. График работы, учет рабочего времени и дисциплина", h1_style))
    story.append(Paragraph("1.1. В компании ООО «ТехноИнновации» установлена 40-часовая пятидневная рабочая неделя с двумя выходными днями (суббота и воскресенье).", body_style))
    story.append(Paragraph("1.2. Базовый рабочий график: начало рабочего дня в 09:00, окончание в 18:00 (в пятницу — до 17:00). Обеденный перерыв составляет 60 минут в промежутке с 13:00 до 14:00. Время обеденного перерыва не включается в рабочее время.", body_style))
    story.append(Paragraph("1.3. Гибкий график: Сотрудники по предварительному согласованию с непосредственным руководителем могут сдвигать начало рабочего дня в интервале от 08:00 до 11:00 при условии отработки суммарно 8 рабочих часов в день.", body_style))
    story.append(Paragraph("1.4. Опоздания и отсутствие: О любом опоздании или вынужденном отсутствии сотрудник обязан проинформировать руководителя и HR-отдел не позднее 09:30 утра по электронной почте или в корпоративном мессенджере.", body_style))

    story.append(Spacer(1, 10))

    # SECTION 2
    story.append(Paragraph("Раздел 2. Порядок удаленной и гибридной работы", h1_style))
    story.append(Paragraph("2.1. Право на гибридный или полностью удаленный формат работы предоставляется сотрудникам после успешного прохождения испытательного срока.", body_style))
    story.append(Paragraph("2.2. Заявка на удаленную работу оформляется во внутренней системе Jira Service Desk не менее чем за 2 рабочих дня до планируемой даты.", body_style))
    story.append(Paragraph("2.3. Требования к удаленному рабочему месту:", h2_style))
    story.append(Paragraph("• Наличие стабильного интернет-канала с пропускной способностью не менее 50 Мбит/с.", bullet_style))
    story.append(Paragraph("• Обязательное подключение к корпоративной сети исключительно через корпоративный VPN (WireGuard / OpenVPN с двухфакторной аутентификацией 2FA).", bullet_style))
    story.append(Paragraph("• Доступность в корпоративном чате Slack и электронной почте в течение всего рабочего дня с 10:00 до 19:00 по московскому времени.", bullet_style))
    story.append(Paragraph("• Запрещается выполнять рабочие обязанности в публичных незащищенных сетях Wi-Fi (кафе, коворкинги) без активного VPN.", bullet_style))

    story.append(PageBreak())

    # SECTION 3
    story.append(Paragraph("Раздел 3. Информационная безопасность и защита конфиденциальных данных", h1_style))
    story.append(Paragraph("3.1. Парольная политика: Пароли к учетным записям должны содержать не менее 12 символов, включая заглавные и строчные буквы, цифры и специальные символы. Срок действия пароля составляет 90 дней, после чего система требует обязательную смену пароля. Повторное использование последних 5 паролей запрещено.", body_style))
    story.append(Paragraph("3.2. Использование съемных носителей: Категорически запрещается подключать к корпоративным ноутбукам и серверам неавторизованные личные USB-накопители, внешние жесткие диски и смартфоны в режиме передачи данных. Все USB-порты на рабочих станциях подлежат централизованному аудиту DLP-системой.", body_style))
    story.append(Paragraph("3.3. Передача конфиденциальной информации: Запрещается передавать исходный код, клиентские базы данных, финансовую отчетность и персональные данные сотрудников через публичные файлообменники, личные почтовые ящики (@gmail.com, @mail.ru, @yandex.ru) или сторонние мессенджеры.", body_style))
    story.append(Paragraph("3.4. Блокировка экрана: При оставлении рабочего места даже на короткое время сотрудник обязан заблокировать экран компьютера комбинацией клавиш Win + L (или Cmd + Ctrl + Q для macOS).", body_style))

    story.append(Spacer(1, 10))

    # SECTION 4
    story.append(Paragraph("Раздел 4. Социальный пакет, компенсации и корпоративное обучение", h1_style))
    story.append(Paragraph("4.1. Добровольное медицинское страхование (ДМС): Полис ДМС с расширенным покрытием, включая экстренную помощь и стоматологию, оформляется каждому сотруднику после прохождения 3 месяцев испытательного срока за счет средств компании.", body_style))
    story.append(Paragraph("4.2. Бюджет на спорт и оздоровление: Компания компенсирует расходы на абонементы в фитнес-клубы, бассейны и спортивные секции в размере до 35 000 рублей в год на одного сотрудника. Выплаты производятся раз в полгода на основании чеков и договоров.", body_style))
    story.append(Paragraph("4.3. Обучение и сертификация: Ежегодный бюджет на профессиональное развитие составляет до 80 000 рублей на каждого штатного сотрудника. Бюджет может быть израсходован на профильные курсы, участие в конференциях и сдачу сертификационных экзаменов.", body_style))
    story.append(Paragraph("4.4. Изучение иностранных языков: Компания предоставляет бесплатный корпоративный доступ к платформе изучения английского языка для всех сотрудников уровня Middle и выше.", body_style))

    story.append(Spacer(1, 10))

    # TABLE: Summary of Benefits
    story.append(Paragraph("Таблица льгот и компенсаций для сотрудников:", h2_style))
    table_data = [
        [
            Paragraph("Вид компенсации", table_header_style),
            Paragraph("Лимит / Условие", table_header_style),
            Paragraph("Срок активации", table_header_style),
            Paragraph("Документы для выплаты", table_header_style),
        ],
        [
            Paragraph("Полис ДМС + Стоматология", table_cell_style),
            Paragraph("100% покрытие компанией", table_cell_style),
            Paragraph("После 3 месяцев работы", table_cell_style),
            Paragraph("Заявление в HR-портале", table_cell_style),
        ],
        [
            Paragraph("Спорт и фитнес", table_cell_style),
            Paragraph("До 35 000 руб./год", table_cell_style),
            Paragraph("С первого месяца", table_cell_style),
            Paragraph("Кассовые чеки, договор", table_cell_style),
        ],
        [
            Paragraph("Обучение и конференции", table_cell_style),
            Paragraph("До 80 000 руб./год", table_cell_style),
            Paragraph("После 6 месяцев работы", table_cell_style),
            Paragraph("Согласование тимлида, счет", table_cell_style),
        ],
        [
            Paragraph("Изучение английского языка", table_cell_style),
            Paragraph("Бесплатный корпоративный доступ", table_cell_style),
            Paragraph("С первого месяца", table_cell_style),
            Paragraph("Автоматически через HR", table_cell_style),
        ]
    ]

    t = Table(table_data, colWidths=[130, 120, 110, 127])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#F4F4F5")),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E4E4E7")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
    ]))
    story.append(t)

    story.append(PageBreak())

    # SECTION 5
    story.append(Paragraph("Раздел 5. Порядок предоставления отпусков и оформления больничных листов", h1_style))
    story.append(Paragraph("5.1. Ежегодный основной оплачиваемый отпуск составляет 28 календарных дней. Отпуск может быть разделен на части, при этом хотя бы одна из частей должна быть не менее 14 календарных дней.", body_style))
    story.append(Paragraph("5.2. График отпусков утверждается ежегодно до 1 декабря на следующий календарный год. Изменение дат отпуска допускается по согласованию с руководителем не позднее чем за 14 дней до начала отпуска.", body_style))
    story.append(Paragraph("5.3. Больничные листы: При наступлении временной нетрудоспособности сотрудник обязан проинформировать тимлида до 10:00 утра первого дня болезни. Электронный листок нетрудоспособности (ЭЛН) передается в бухгалтерию не позднее 3 дней с момента закрытия больничного.", body_style))
    story.append(Paragraph("5.4. Дополнительные оплачиваемые дни (Day Off): Компания предоставляет до 3 оплачиваемых дней в год без оформления официального больничного листа в случае внезапного легкого недомогания («Day-off»).", body_style))

    story.append(Spacer(1, 10))

    # SECTION 6
    story.append(Paragraph("Раздел 6. Контакты ответственных подразделений и эскалация", h1_style))
    story.append(Paragraph("• Отдел кадров и HR-сопровождение: hr@technoinnovations.ru, внутренний телефон 101, кабинет 304.", bullet_style))
    story.append(Paragraph("• Служба информационной безопасности (SOC): sec@technoinnovations.ru, горячая линия 112 (круглосуточно).", bullet_style))
    story.append(Paragraph("• Бухгалтерия и расчет зарплаты: payroll@technoinnovations.ru, внутренний телефон 105.", bullet_style))
    story.append(Paragraph("• Техническая поддержка и Helpdesk: support@technoinnovations.ru, портал https://helpdesk.technoinnovations.corp", bullet_style))

    doc.build(story, canvasmaker=NumberedCanvas)
    return out_file

if __name__ == "__main__":
    generated_path = generate_company_policy_pdf()
    print(f"Sample PDF generated successfully: {generated_path}")
