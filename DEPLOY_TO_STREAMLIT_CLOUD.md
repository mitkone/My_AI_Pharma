# Как да качиш приложението в Streamlit Cloud

## Бърз старт (5-10 минути)

Streamlit Cloud е **безплатен** и позволява колегите ти да използват приложението от всяко устройство (телефон, таблет, laptop) без да инсталират Python.

---

## Стъпка 1: Подготовка на файловете

### 1.1 Създай `.gitignore` файл

В папката `My_AI_Pharma` създай файл `.gitignore` със следното съдържание:

```
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python

# Virtual environments
venv/
env/
ENV/

# Secrets
.env

# Excel backup files
~$*.xlsx
.~lock.*

# Temporary files
*.log
*.csv
*_melted.csv
*_old*.py

# OS files
.DS_Store
Thumbs.db
```

**Важно:** `.env` с твоя OpenAI API ключ НЕ трябва да се качва в GitHub!

### 1.2 Провери `requirements.txt`

Уверете се че `requirements.txt` съдържа:

```
pandas>=2.0
openpyxl>=3.1
streamlit>=1.28
plotly>=5.0
openai>=1.0
python-dotenv>=1.0
```

---

## Стъпка 2: Качване в GitHub

### 2.1 Създай GitHub account

1. Отиди на [github.com](https://github.com)
2. Sign Up (безплатен account)
3. Потвърди email-а си

### 2.2 Създай ново repository

1. Кликни "New repository" (зеленият бутон)
2. Име: `pharma-data-viz` (или каквото искаш)
3. Описание: "Pharma sales data visualization"
4. **Важно:** Избери **Private** (само ти и хората които поканиш ще го виждат)
5. **НЕ** добавяй README, .gitignore или license (вече имаш)
6. Кликни "Create repository"

### 2.3 Качи файловете

**Вариант A: GitHub Desktop (лесен)**

1. Инсталирай [GitHub Desktop](https://desktop.github.com/)
2. File → Add Local Repository → избери `My_AI_Pharma` папката
3. "Create a repository" → "Publish repository"
4. Махни отметката от "Keep this code private" ако искаш публичен (препоръчвам Private)
5. Publish

**Вариант B: Git command line**

Отвори Command Prompt в `My_AI_Pharma` папката:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/твоят-username/pharma-data-viz.git
git push -u origin main
```

(Замени `твоят-username` и `pharma-data-viz` с реалните имена)

### 2.4 Провери какво е качено

Отвори repo-то в браузър и провери дали виждаш:
- ✅ `app.py`, `config.py`, `ui_components.py` и т.н.
- ✅ Всички `.xlsx` файлове (Lipocante, Antihistamines, и т.н.)
- ❌ **НЕ** трябва да виждаш `.env` файл!

---

## Стъпка 3: Deploy на Streamlit Cloud

### 3.1 Регистрация

1. Отиди на [share.streamlit.io](https://share.streamlit.io)
2. Кликни "Sign up" или "Get started"
3. Избери "Continue with GitHub"
4. Разреши на Streamlit да има достъп до твоя GitHub account

### 3.2 Deploy приложението

1. Кликни "New app"
2. Избери:
   - **Repository:** `твоят-username/pharma-data-viz`
   - **Branch:** `main`
   - **Main file path:** `app.py`
3. **Advanced settings** (кликни):
   - **Python version:** 3.11 (или 3.10+)
   
4. **Secrets** (ВАЖНО за AI функцията):
   Копирай съдържанието на твоя `.env` файл тук:
   ```
   OPENAI_API_KEY="sk-proj-твоят-ключ-тук"
   ```
   (Без кавички около ключа)

5. Кликни "Deploy!"

### 3.3 Изчакай deployment (2-5 минути)

Ще видиш лог messages:
- Installing dependencies...
- Loading data...
- App is running!

**URL адресът ще бъде нещо от сорта на:**
```
https://твоят-username-pharma-data-viz-app-xxxx.streamlit.app
```

---

## Стъпка 4: Сподели с колеги

### Споделяне на URL

1. Копирай URL адреса (напр. `https://твоят-app.streamlit.app`)
2. Изпрати го на колегите си
3. Те отварят линка - **не е нужна регистрация**, директно виждат приложението!

### Ако е Private repo

По подразбиране Private repos са достъпни само за теб. За да дадеш достъп:

**Опция 1: Направи repo публичен**
- GitHub → Settings → Danger Zone → Change visibility → Public

**Опция 2: Покани specific хора (препоръчвам)**
- GitHub → Settings → Collaborators → Add people
- Добави GitHub username-ите на колегите

**Опция 3: Deploy от public repo**
- Създай ново public repo специално за production
- Копирай файловете там (без `.env`!)

---

## Управление след deployment

### Обновяване на данни

Когато качиш нови Excel файлове:

1. Копирай новите `.xlsx` в папката `My_AI_Pharma`
2. Git commit & push:
   ```bash
   git add *.xlsx
   git commit -m "Add new data"
   git push
   ```
3. Streamlit Cloud **автоматично ще redeploy-не** приложението (2-3 минути)

### Обновяване на код

Промяна в `app.py`, `ui_components.py` и т.н.:

1. Направи промените локално
2. Git commit & push:
   ```bash
   git add .
   git commit -m "Fix bug / Add feature"
   git push
   ```
3. Auto-redeploy

### Принудително restart

Ако приложението "закъса":
- Streamlit Cloud dashboard → твоето app → ⋮ (three dots) → "Reboot app"

### Проверка на logs

- Dashboard → твоето app → "Manage app" → вижда се real-time log

---

## Troubleshooting

### Грешка: "ModuleNotFoundError"

**Решение:** Добави липсващия модул в `requirements.txt` и push:
```
git add requirements.txt
git commit -m "Add missing dependency"
git push
```

### Грешка: "File not found: *.xlsx"

**Решение:** Провери дали Excel файловете са в GitHub repo (не са в .gitignore).

### AI не работи

**Решение:** Провери Secrets в Streamlit Cloud dashboard:
- "Manage app" → "Settings" → "Secrets"
- Добави `OPENAI_API_KEY="sk-..."`

### Приложението е бавно

**Причини:**
- Streamlit Cloud free tier има shared resources
- При първо зареждане на данните отнема време (800k+ редове)

**Решение:**
- Кешът `@st.cache_data` намалява последващите зареждания
- За production: размисли за Streamlit Cloud Business ($200/мес)

### Прекалено много данни

Streamlit Cloud Free tier има limit:
- **1 GB RAM** за приложението
- **1 GB storage** за repo

Ако се блъснеш в limit:
- Архивирай стари Excel файлове (премести ги от repo)
- Пази само последните 2 години данни

---

## Алтернативи на Streamlit Cloud

### 1. ngrok (локално, временно)

За бързо тестване без deploy:

```bash
# Инсталирай ngrok
# Стартирай Streamlit локално
python -m streamlit run app.py

# В друг терминал:
ngrok http 8501
```

URL: `https://xxxx-xxx-xxx.ngrok-free.app` (валиден докато ngrok работи)

**Минуси:** Трябва да държиш лаптопа включен.

### 2. Heroku (платен)

- По-скъп от Streamlit Cloud
- Повече control

### 3. AWS / GCP (напреднало)

- Най-скъп
- Изисква технически умения

---

## Безопасност

### Пароли за достъп

Ако искаш да защитиш приложението с парола:

1. Инсталирай `streamlit-authenticator`:
   ```
   pip install streamlit-authenticator
   ```

2. Добави в началото на `app.py`:
   ```python
   import streamlit_authenticator as stauth
   
   names = ['Admin', 'Kolega1']
   usernames = ['admin', 'kolega1']
   passwords = ['pass123', 'pass456']  # Хеширани в production!
   
   hashed_passwords = stauth.Hasher(passwords).generate()
   authenticator = stauth.Authenticate(names, usernames, hashed_passwords,
       'pharma_app', 'secret_key', cookie_expiry_days=30)
   
   name, authentication_status, username = authenticator.login('Login', 'main')
   
   if not authentication_status:
       st.stop()
   ```

3. Update requirements.txt, commit & push

### HTTPS

Streamlit Cloud автоматично използва HTTPS - данните са криптирани.

---

## Поддръжка

### Колко струва?

- **Streamlit Community Cloud:** Безплатен
  - 1 private app
  - Unlimited public apps
  - 1 GB RAM / app
  - Shared CPU

- **Streamlit Cloud Business:** $200-500/месец
  - Unlimited private apps
  - 2-8 GB RAM
  - Dedicated CPU
  - Custom domains

### Мониторинг

Streamlit Cloud показва:
- Брой посетители (viewers)
- Uptime
- Resource usage

### Support

- [Streamlit Community Forum](https://discuss.streamlit.io/)
- [Streamlit Docs](https://docs.streamlit.io/)

---

## Следващи стъпки

След успешен deploy:

1. **Тествай от телефон и laptop**
   - Провери всички функции
   - Потребителски опит на мобилни

2. **Събери feedback от колеги**
   - Какво е объркващо?
   - Какво липсва?

3. **Optimize**
   - Добави tutorials/помощни текстове
   - Подобри performance

4. **Monitor**
   - Провери logs за errors
   - Следи за необичайна активност

---

## Бърз checklist

- [ ] Създаден `.gitignore` (без `.env`!)
- [ ] GitHub account
- [ ] Repo създадено (Private препоръчвам)
- [ ] Файлове качени (включително .xlsx)
- [ ] Streamlit Cloud account
- [ ] App deployed
- [ ] Secrets добавени (OPENAI_API_KEY)
- [ ] URL работи
- [ ] Тествано от телефон
- [ ] Споделено с колеги

---

**Готово! Приложението ти е онлайн и достъпно от цял свят! 🎉**

За въпроси: Streamlit Community Forum или виж README_REFACTORED.md за технически детайли.
