# Мобилна оптимизация на Pharma Data Viz

## Направени промени за мобилни устройства

### 1. Layout и структура

**config.py:**
```python
LAYOUT = "centered"  # Вместо "wide" за по-добро мобилно изживяване
MOBILE_OPTIMIZED = True
```

**Защо:** Centered layout се адаптира по-добре към тесни екрани. Wide layout създава хоризонтален скрол на мобилни.

---

### 2. Височина на графики

**config.py:**
```python
CHART_HEIGHT = 600  # Увеличено от 500
BRICK_CHART_HEIGHT = 550  # Увеличено от 450
```

**Защо:** На малък екран по-високите графики са по-четливи. Потребителят скролва вертикално, което е естествено за мобилни.

---

### 3. Легенди на графиките

**ui_components.py - Всички графики:**
```python
legend=dict(
    orientation="h",  # Хоризонтална легенда
    yanchor="bottom",
    y=-0.3,  # Под графиката
    xanchor="center",
    x=0.5
)
```

**Защо:** 
- Вертикалната легенда отнема много място на тесен екран
- Хоризонталната легенда под графиката е по-компактна
- Центрирана е по-добре от страничната позиция

---

### 4. Шрифтове

**ui_components.py:**
```python
font=dict(size=12)  # Увеличено от 10 (по подразбиране)
```

**Защо:** По-големите шрифтове са по-четливи на малки екрани.

---

### 5. Margin (отстояния)

```python
margin=dict(b=120, t=80, l=50, r=50)  # Timeline charts
margin=dict(b=100, t=80, l=50, r=50)  # Bar charts
```

**Защо:** 
- `b=120` - повече място отдолу за легендата
- Предотвратява припокриване на текст

---

### 6. Премахване на horizontal layouts

**ui_components.py:**
```python
# ПРЕДИ:
level = st.radio(..., horizontal=True)

# СЛЕД:
level = st.radio(...)  # Вертикално по подразбиране
```

**Защо:** Хоризонталните radio бутони се скъсяват на малък екран. Вертикалните са по-четливи.

---

### 7. Sidebar винаги свит на мобилни

Streamlit автоматично свива sidebar на мобилни устройства (<= 768px ширина).

**Как работи:**
- На десктоп: Sidebar е отворен по подразбиране
- На мобилен: Sidebar е затворен, отваря се с бутон ☰

---

## Тестване на различни устройства

### Chrome DevTools (Симулатор)

1. Отвори приложението: http://127.0.0.1:8501
2. Натисни `F12` (Developer Tools)
3. Кликни на иконата за устройства (Device Toolbar) или `Ctrl+Shift+M`
4. Избери:
   - iPhone 12 Pro (390 x 844)
   - iPhone SE (375 x 667)
   - Galaxy S20 (360 x 800)
   - iPad Air (820 x 1180)

### Реални устройства

Провери на реален телефон:
1. Свържи телефона в същата WiFi мрежа като лаптопа
2. Отвори http://192.168.x.x:8501 (IP на лаптопа)
3. Тествай скролването, zoom, филтрите

---

## Best Practices за мобилни Streamlit апликации

### ✅ Препоръчва се

1. **Вертикални layouts** - st.radio(), st.selectbox() без columns
2. **Кратки етикети** - "Регион" вместо "Избери регион от списъка"
3. **Touch-friendly бутони** - По-големи размери (Streamlit автоматично)
4. **Scrollable dataframes** - `st.dataframe(..., height=300)` вместо цялата таблица
5. **Expandеrs за допълнителна информация** - Скрива съдържание докато не е нужно

### ❌ Избягвай

1. **st.columns() с много колони** - Скъсява съдържанието
2. **Horizontal radio с много опции** - Излиза извън екрана
3. **Wide layout** - Създава хоризонтален скрол
4. **Малки шрифтове** - Трудно четими
5. **Фиксирана ширина в px** - Винаги ползвай `use_container_width=True`

---

## Как да превключваш между Desktop и Mobile layout

Ако искаш Desktop ("wide") и Mobile ("centered") режими:

### Вариант 1: Ръчно превключване

**config.py:**
```python
# За Desktop:
LAYOUT = "wide"

# За Mobile:
LAYOUT = "centered"
```

### Вариант 2: Автоматично detection (напреднало)

```python
# app.py
import streamlit as st

# Проверка за ширина на екрана (JS injection)
is_mobile = st.session_state.get('is_mobile', False)

if is_mobile:
    st.set_page_config(layout="centered")
else:
    st.set_page_config(layout="wide")
```

**Забележка:** Streamlit не поддържа native mobile detection. Най-простото е:
- Production deployment: `layout="centered"` (работи добре и на desktop)
- Вътрешен desktop use: `layout="wide"`

---

## Размери на екрани

| Устройство          | Ширина (px) | Streamlit Behavior        |
|---------------------|-------------|---------------------------|
| iPhone SE           | 375         | Sidebar свит              |
| iPhone 12 Pro       | 390         | Sidebar свит              |
| Galaxy S20          | 360         | Sidebar свит              |
| iPad Mini           | 744         | Sidebar свит              |
| iPad Air            | 820         | Sidebar отворен (narrow)  |
| Desktop (1080p)     | 1920        | Sidebar отворен           |

**Breakpoint:** Streamlit свива sidebar при ширина <= 768px.

---

## Performance на мобилни

**Оптимизации:**

1. **Кеширане:**
   ```python
   @st.cache_data(ttl=300)
   def get_cached_data():
       ...
   ```
   - Данните се зареждат веднъж на 5 мин
   - Бързо презареждане при смяна на филтри

2. **Lazy loading на графики:**
   - Графиките се създават само в активния таб
   - st.tabs() показва една графика наведнъж

3. **Plotly vs Altair:**
   - Plotly е интерактивен, но по-тежък (избран тук)
   - За много графики: размисли за Altair (по-лек)

---

## Известни проблеми

### 1. Zoom на iOS
Safari на iPhone понякога zoom-ва автоматично input полета.

**Workaround:** Няма пълно решение, но Streamlit input-ите са оптимизирани.

### 2. Keyboard overlay
Когато се отвори клавиатурата, тя може да скрие input полето.

**Решение:** Streamlit автоматично скролва до активното поле.

### 3. Touch gestures
Plotly графиките поддържат pinch-to-zoom и pan на mobile.

---

## Deployment препоръки

### Streamlit Cloud
- Автоматично мобилно-оптимизиран
- Използвай `layout="centered"` в config за production

### ngrok (временно)
- Работи отлично на локална мрежа
- Добър за демонстрации

### Custom domain
- Добави viewport meta tag ако host-ваш в iframe:
  ```html
  <meta name="viewport" content="width=device-width, initial-scale=1">
  ```

---

## Следващи стъпки за още по-добра мобилна оптимизация

1. **Progressive Web App (PWA)**
   - Добави manifest.json
   - Позволява "Add to Home Screen"

2. **Dark mode**
   - Streamlit 1.29+ поддържа native dark theme
   - По-малко battery drain на OLED екрани

3. **Offline mode**
   - Service worker за кеширане
   - Работа без интернет (напреднало)

4. **Push notifications**
   - Известия за нови данни
   - Изисква backend integration
