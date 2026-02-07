# Pharma Data Viz - Рефакторирана структура

## Обзор

Професионално структурирано приложение за визуализация на фармацевтични продажби.
Кодът е разделен на модули за лесна поддръжка, тестване и разширяване.

---

## Структура на проекта

```
My_AI_Pharma/
├── app.py                      # Главно Streamlit приложение (само UI)
├── config.py                   # Конфигурация и константи
├── data_processing.py          # Зареждане и обработка на данни
├── ui_components.py            # UI компоненти (филтри, графики)
├── ai_analysis.py              # AI анализ с OpenAI
├── process_excel_hierarchy.py  # Обработка на йерархични Excel файлове
├── drug_molecules.py           # Маппинг на медикаменти към молекули
├── update_molecules.py         # Инструмент за обновяване на молекули
├── requirements.txt            # Python зависимости
├── run_app.bat                 # Лаунчер за Windows
├── .env                        # API ключове (не се комитва в Git!)
└── *.xlsx                      # Excel файлове с данни

Backup файлове:
├── app_old_backup.py           # Стар app.py преди рефакторирането
├── process_excel_hierarchy_old.py  # Стар process_excel_hierarchy.py
```

---

## Модули и отговорности

### 1. `config.py` - Конфигурация

Централизирана конфигурация на проекта:
- Пътища до директории
- Streamlit настройки (заглавие, layout, cache TTL)
- Задължителни/опционални колони в данните
-Periodi (тримесечия, месеци, години)
- Метрики и визуализации
- AI настройки (модел, max tokens)

**Защо отделен файл?** Лесно променяме настройки без да търсим в кода.

---

### 2. `data_processing.py` - Обработка на данни

**Функции:**

#### `validate_dataframe(df, filename) -> (bool, str)`
Валидира дали DataFrame има задължителните колони (Region, Drug_Name, Quarter, Units).

#### `clean_column_names(df) -> DataFrame`
Почиства имената на колоните: премахва интервали, специални символи.

#### `extract_source_name(filename) -> str`
Извлича категория от име на файл: `"Lipocante Total Q.xlsx"` → `"Lipocante"`

#### `load_single_excel(filepath) -> DataFrame | None`
Зарежда един Excel файл:
1. Обработва йерархията с `process_pharma_excel()`
2. Валидира данните
3. Почиства колоните
4. Добавя колона `Source` (категория)

#### `load_all_excel_files(data_dir) -> DataFrame`
Зарежда всички .xlsx от директорията и ги обединява.

#### `prepare_data_for_display(df) -> DataFrame`
Подготвя данните за визуализация:
- Добавя колона `Molecule` (от `drug_molecules.py`)
- Конвертира `Units` в числа
- Премахва редове без валидни Units

#### `get_period_sort_key(period) -> (str, int)`
Функция за сортиране на периоди (Q1 2023, Jan 2024).

#### `get_sorted_periods(df) -> List[str]`
Връща сортиран списък от периоди.

**Защо отделен модул?** Бизнес логиката е независима от UI – може да се тества без Streamlit.

---

### 3. `process_excel_hierarchy.py` - Excel обработка

Обработва йерархични Excel файлове (Region → District → Category → Drug).

**Главна функция:**

#### `process_pharma_excel(filepath, sheet_name, save) -> DataFrame`

**Стъпки:**
1. Чете Excel файла
2. Разпознава колони с периоди (Q1 2023, Jan 2024...)
3. Идентифицира типове редове:
   - Region: `"Region SOFIA"`
   - District: `"(PH) BANSKO"`
   - Category: `"R06A0 Antihistamines"`
   - Drug: `"AERIUS"`, `"ALLEGRA"`...
4. Попълва йерархията надолу с `ffill()` (forward fill)
5. Филтрира само Drug редове (data rows)
6. Преобразува в long format с `pd.melt()`

**Резултат:**
```
Region         | District      | Drug_Name | Quarter  | Units
Region SOFIA   | (PH) BANSKO   | AERIUS    | Q1 2023  | 150
Region SOFIA   | (PH) BANSKO   | AERIUS    | Q2 2023  | 180
...
```

**Подробобрения:**
- Детайлни Bulgarian коментари
- Error handling с custom exception `ExcelProcessingError`
- Logging на всяка стъпка
- Помощни функции: `_detect_sheet_name()`, `_detect_period_columns()`, `_identify_row_types()`, `_fill_hierarchy()`

---

### 4. `ui_components.py` - UI компоненти

Преизползваеми Streamlit компоненти.

**Функции:**

#### `create_filters(df) -> dict`
Създава sidebar филтри: регион, медикамент, молекула, brick, конкуренти.
Връща речник с избраните стойности.

#### `apply_filters(df, filters) -> DataFrame`
Прилага избраните филтри върху данните.

#### `create_metric_selector() -> (str, bool)`
Създава селектор за метрика (Units, EV Index, Market Share, % Ръст).

#### `calculate_metric_data(...) -> (DataFrame, str, str)`
Изчислява избраната метрика:
- **Units**: Сумира опаковките
- **EV Index**: (Units_сега / Units_преди_4_периода) * 100
- **Market Share**: (Units_продукт / Units_всички) * 100
- **% Ръст**: Процент промяна спрямо предишен период

#### `create_timeline_chart(...)`
Създава линейна графика с Plotly (основен продукт + конкуренти).

#### `create_brick_charts(...)`
Създава bar charts по региони и brick-ове.

**Защо отделен модул?** UI компонентите могат да се преизползват в други табове или приложения.

---

### 5. `ai_analysis.py` - AI анализ

AI анализ с OpenAI GPT.

**Функции:**

#### `check_api_key() -> bool`
Проверява дали `OPENAI_API_KEY` е зададен.

#### `build_data_context(df, sel_product, competitors) -> str`
Изгражда текстов контекст от данните:
- Продукт и региони
- Продажби по регион
- Тренд по периоди
- Конкуренти

#### `get_ai_analysis(question, data_context) -> str | None`
Изпраща въпрос + контекст към OpenAI и връща анализ.

#### `render_ai_analysis_tab(df, sel_product, competitors)`
Рендира цял таб с AI анализ в Streamlit.

**Пример за промпт:**
```
Ти си бизнес анализатор на фармацевтични продажби.

**Данни:**
Продукт: Lipocante
Опаковки по регион: Region SOFIA=12000, Region PLEVEN=8500...
Тренд: Q1 2023=1000, Q2 2023=1200...

**Въпрос:**
Защо Lipocante в Sofia не расте като в Pleven?

Отговори на български с причини и препоръки.
```

**Настройка:** Добави `OPENAI_API_KEY=sk-...` във файл `.env`.

---

### 6. `app.py` - Главно приложение

**Чист UI код - само оркестриране:**

```python
# Зареждане на данни
df_raw = get_cached_data()

# Филтри
filters = create_filters(df_raw)
df_filtered = apply_filters(df_raw, filters)

# Метрика
metric, share_in_molecule = create_metric_selector()

# Табове
with tab_timeline:
    df_agg, y_col, y_label = calculate_metric_data(...)
    create_timeline_chart(...)

with tab_brick:
    create_brick_charts(...)

with tab_ai:
    render_ai_analysis_tab(...)
```

**Кеширане:**
```python
@st.cache_data(ttl=300)  # 5 минути
def get_cached_data():
    df = load_all_excel_files()
    return prepare_data_for_display(df)
```

---

## Предимства на рефакторирането

### 1. **Разделени отговорности (Separation of Concerns)**
- Всеки модул има ясна цел
- Промяна в UI не засяга бизнес логиката

### 2. **Лесно тестване**
```python
# Тестване на data_processing без Streamlit
from data_processing import load_all_excel_files
df = load_all_excel_files()
assert len(df) > 0
```

### 3. **Преизползваемост**
UI компоненти могат да се използват в други приложения.

### 4. **Четимост**
Bulgarian коментари обясняват всяка стъпка:
```python
# Попълва йерархията надолу с ffill()
# Пример: Region SOFIA → всички следващи редове са в Sofia
df["Region"] = df["Region"].ffill()
```

### 5. **Error Handling**
Валидация на данни и ясни съобщения за грешки:
```python
if df.empty:
    return False, f"Файлът {filename} е празен"
```

### 6. **Logging**
Всяка стъпка се логва:
```
INFO: Зареждане на Lipocante Total Q.xlsx...
INFO: Открити 12 тримесечия
INFO: Разпознати 14 региона, 292 района, 12522 медикамента
INFO: ✓ Липocante Total Q.xlsx: 150264 реда
```

---

## Как да разшириш проекта

### Добавяне на нова метрика

1. Добави метриката в `config.py`:
   ```python
   METRICS = [..., "YoY Growth (%)"]
   ```

2. Добави изчисление в `ui_components.py → calculate_metric_data()`:
   ```python
   elif metric == "YoY Growth (%)":
       # Изчисли year-over-year ръст
       ...
   ```

### Добавяне на нов таб

1. Създай функция в `ui_components.py`:
   ```python
   def create_comparison_tab(df, products):
       st.subheader("Сравнение")
       # твоята логика...
   ```

2. Добави таба в `app.py`:
   ```python
   tab1, tab2, tab3, tab_new = st.tabs([...])
   with tab_new:
       create_comparison_tab(df, products)
   ```

### Добавяне на нов тип данни

1. Обнови `config.py → REQUIRED_COLUMNS` ако има нови колони
2. Добави обработка в `process_excel_hierarchy.py` ако е нов формат
3. Обнови валидацията в `data_processing.py`

---

## Тестване

### Бърз тест на модулите:

```bash
python test_refactor.py
```

### Тест на Excel обработка:

```bash
python process_excel_hierarchy.py "Lipocante Total Q.xlsx"
```

### Стартиране на приложението:

```bash
python -m streamlit run app.py
```
или
```bash
run_app.bat
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'config'"
**Решение:** Уверете се, че всички .py файлове са в същата папка.

### "ExcelProcessingError: Не са открити колони с периоди"
**Решение:** Проверете дали Excel има колони с "Q1 2023" или "Jan 2023" формат.

### AI не работи
**Решение:** 
1. Създайте `.env` файл с `OPENAI_API_KEY=sk-...`
2. Инсталирайте: `pip install python-dotenv openai`

### Данните се зареждат бавно
**Решение:** Кешът е 5 минути. За по-дълго кеширане: `config.py → CACHE_TTL = 600`.

---

## Миграция от старата версия

Старият код е бекъпнат в:
- `app_old_backup.py`
- `process_excel_hierarchy_old.py`

Ако имате проблеми, можете да върнете старата версия:
```bash
copy app_old_backup.py app.py
```

---

## Контакти и поддръжка

За въпроси или проблеми, проверете:
1. Логовете в конзолата (INFO/WARNING/ERROR)
2. Streamlit error messages
3. Bulgarian коментарите в кода за обяснения

Всеки модул има подробна документация в docstring-овете.
