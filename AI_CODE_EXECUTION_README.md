# 🤖 AI Analyst с Code Execution

## Какво е новото?

**Upgraded AI Analyst** сега може да:
- ✅ **Пише Python код** динамично
- ✅ **Изпълнява кода** безопасно (sandbox)
- ✅ **Чете директно** от `master_data.csv`
- ✅ **Генерира Plotly графики** автоматично
- ✅ **Връща текст + визуализация**
- ✅ **Mobile-optimized** display

---

## 🚀 Как работи?

### Стъпка 1: Потребителят задава въпрос
```
"Колко е ръстът на ЛИПОКАНТ в София през Q4 2025?"
```

### Стъпка 2: AI пише Python код
```python
# Load data
df = pd.read_csv(master_data_path)

# Analysis
sofia_data = df[
    (df['Drug_Name'] == 'LIPOCANTE') & 
    (df['Region'] == 'Region Sofia') &
    (df['Quarter'] == 'Q4 2025')
]
q4_units = sofia_data['Units'].sum()

# Previous quarter for comparison
q3_units = df[
    (df['Drug_Name'] == 'LIPOCANTE') & 
    (df['Region'] == 'Region Sofia') &
    (df['Quarter'] == 'Q3 2025')
]['Units'].sum()

growth = ((q4_units - q3_units) / q3_units * 100) if q3_units > 0 else 0

result = f"Ръст на ЛИПОКАНТ в София (Q4 2025): {growth:.1f}%"

# Visualization
quarterly_trend = df[
    (df['Drug_Name'] == 'LIPOCANTE') & 
    (df['Region'] == 'Region Sofia')
].groupby('Quarter')['Units'].sum().reset_index()

fig = px.line(
    quarterly_trend, 
    x='Quarter', 
    y='Units',
    title='ЛИПОКАНТ - София (тренд)'
)
```

### Стъпка 3: Кодът се изпълнява безопасно

### Стъпка 4: Резултати се показват
- 📝 **Текст**: "Ръст на ЛИПОКАНТ в София (Q4 2025): 12.5%"
- 📈 **Графика**: Line chart с тренда
- 🔍 **Генериран код**: Може да се види за transparency

---

## 🔒 Сигурност (Sandbox)

Code executor използва **sandboxed environment**:

### ✅ Разрешени операции:
- `pd.read_csv(master_data_path)` - Четене на данни
- Pandas операции (filter, groupby, merge, etc.)
- Plotly визуализации (px, go)
- Python built-ins (print, sum, min, max, etc.)

### ❌ Блокирани операции:
- `import os` / `import sys` - Системни операции
- `open()` / `write()` / `delete()` - Файлови операции
- `subprocess` / `system()` - Команди
- `eval()` / `compile()` - Dynamic code execution
- Network операции

**Резултат: Безопасно изпълнение без риск за системата!**

---

## 📱 Mobile Optimization

### Chart настройки:
```python
fig.update_layout(
    height=400,  # По-ниска за mobile
    margin=dict(l=40, r=40, t=40, b=100),
    font=dict(size=11),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=-0.3,  # Долу
        xanchor="center",
        x=0.5
    ),
    xaxis=dict(tickangle=-45)
)
```

### Display настройки:
```python
st.plotly_chart(
    fig,
    use_container_width=True,  # Responsive width
    config={'displayModeBar': False}  # Скрит toolbar за mobile
)
```

**Резултат: Графиките изглеждат отлично на мобилни устройства!**

---

## 💡 Примерни въпроси

### Ръст и спад:
- "Колко е ръстът на ЛИПОКАНТ през последните 3 тримесечия?"
- "В кои региони спада AERIUS и защо?"
- "Кое тримесечие е най-доброто за LIPOCANTE?"

### Регионален анализ:
- "Кой регион има най-високи продажби на ЛИПОКАНТ?"
- "Сравни София с Пловдив за AERIUS"
- "В кои brick-ове растем най-много?"

### Конкурентен анализ:
- "Как се справям срещу CRESTOR в София?"
- "Кой конкурент расте най-бързо?"
- "Каква е разликата между мен и топ 3 конкуренти?"

### Сложни анализи:
- "Покажи корелация между региони и ръст"
- "Анализирай сезонността на продажбите"
- "Прогнозирай продажбите за следващото тримесечие"

---

## 🎯 Workflow

```
1. Потребител задава въпрос
        ↓
2. AI получава question + data summary
        ↓
3. AI генерира Python код
        ↓
4. Код се валидира (security check)
        ↓
5. Код се изпълнява (sandbox)
        ↓
6. Резултати се показват:
   - Text summary
   - Plotly chart (if applicable)
   - Generated code (for transparency)
```

---

## 🔧 Технически детайли

### Компоненти:

1. **`ai_code_executor.py`**
   - `safe_exec()` - Безопасно изпълнение
   - `generate_analysis_code()` - Prompt engineering
   - `validate_code_safety()` - Security validation
   - `create_mobile_friendly_figure()` - Mobile optimization

2. **`ai_analysis.py`**
   - `execute_ai_code_analysis()` - Main orchestrator
   - `render_ai_analysis_tab()` - UI rendering

3. **`master_data.csv`**
   - Централна база данни
   - 701,113 реда
   - Long format за лесен анализ

### Dependencies:
- `openai>=1.0` - AI модел
- `pandas>=2.0` - Data manipulation
- `plotly>=5.0` - Visualization

---

## 📊 Пример: Пълен execution flow

### Input:
```
Въпрос: "Кой регион има най-висок ръст на ЛИПОКАНТ?"
```

### AI генерира код:
```python
df = pd.read_csv(master_data_path)

# Filter ЛИПОКАНТ data
lipocante = df[df['Drug_Name'] == 'LIPOCANTE']

# Calculate growth by region
regions = lipocante['Region'].unique()
growth_by_region = []

for region in regions:
    region_data = lipocante[lipocante['Region'] == region]
    quarters = sorted(region_data['Quarter'].unique())
    
    if len(quarters) >= 2:
        last_q = region_data[region_data['Quarter'] == quarters[-1]]['Units'].sum()
        first_q = region_data[region_data['Quarter'] == quarters[0]]['Units'].sum()
        growth = ((last_q - first_q) / first_q * 100) if first_q > 0 else 0
        growth_by_region.append({'Region': region, 'Growth_%': growth})

growth_df = pd.DataFrame(growth_by_region).sort_values('Growth_%', ascending=False)
top_region = growth_df.iloc[0]

result = f"Най-висок ръст: {top_region['Region']} с {top_region['Growth_%']:.1f}%"

# Chart
fig = px.bar(growth_df.head(10), x='Region', y='Growth_%', 
             title='ЛИПОКАНТ - Ръст по региони')
fig.update_layout(height=400, xaxis_tickangle=-45)
```

### Output:
- **Text**: "Най-висок ръст: Region Plovdiv с 45.2%"
- **Chart**: Bar chart с топ 10 региона
- **Code**: Генерираният Python код (за transparency)

---

## ⚠️ Limitations

### Какво НЕ може:
- ❌ Системни операции (file write, delete, network)
- ❌ Import на произволни библиотеки
- ❌ Достъп до OS environment
- ❌ Long-running computations (>30s timeout)

### Какво може:
- ✅ Всички Pandas операции
- ✅ Plotly визуализации
- ✅ Statistical анализи
- ✅ Aggregations, joins, pivots
- ✅ Filtering, sorting, grouping

---

## 🎨 Mobile-Friendly Display

### Charts:
- Fixed height: **400px** (идеален за мобилни)
- Legends at bottom (не obstruct data)
- Responsive width (`use_container_width=True`)
- Hidden toolbar for cleaner look

### Containers:
- Вертикално подреждане
- Expandable sections (код, детайли)
- Clear visual hierarchy

---

## 🔄 Error Handling

Ако кодът има грешка:
1. AI получава error message
2. Може да опита отново (future feature)
3. Потребителят вижда грешката и генерирания код
4. Може да редактира въпроса и пробва отново

---

## 🚀 Предимства

### Преди (Stар AI Analyst):
- Само текстов анализ
- Без визуализации
- Ограничен context (само показаните данни)
- Статични отговори

### Сега (Upgraded AI Analyst):
- **Dynamic code generation**
- **Custom визуализации за всеки въпрос**
- **Пълен достъп до master_data.csv** (701k+ реда)
- **Flexible analysis** (може да прави всичко с Pandas)

**10x по-мощен AI анализ!** 🚀

---

## 📚 За разработчици

### Добавяне на нови разрешени операции:

Редактирай `ai_code_executor.py`:

```python
safe_globals = {
    'pd': pd,
    'px': px,
    'go': go,
    'np': np,  # Нова библиотека
    # ... други
}
```

### Промяна на timeout:

```python
result = safe_exec(code, master_path, timeout=60)  # 60 секунди
```

### Custom prompt engineering:

Редактирай `generate_analysis_code()` в `ai_code_executor.py`

---

## ✅ Заключение

AI Analyst сега е **full-featured data science tool**:
- Пише код автоматично
- Изпълнява го безопасно
- Генерира custom визуализации
- Оптимизиран за мобилни

**Perfect за non-technical потребители които искат advanced анализи!** 🎯
