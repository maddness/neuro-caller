# 🚀 Следующие шаги для запуска Neuro-Caller

## ✅ Что уже готово:

- ✅ Виртуальное окружение создано
- ✅ Зависимости установлены
- ✅ Файл `.env` настроен с учетными данными:
  - Account ID: `9999956`
  - Application ID: `11963388`
  - Rule ID: `3769281`
  - Телефон: `+74999384362`
  - Бренд: **Янго**

---

## 📝 Что нужно сделать СЕЙЧАС:

### 1️⃣ Загрузить сценарий в Voximplant Cloud IDE (5 минут)

1. **Откройте панель Voximplant**:
   - Перейдите на [manage.voximplant.com](https://manage.voximplant.com)
   - Войдите в аккаунт `maddness.n8`

2. **Найдите приложение**:
   - В левом меню → **Applications**
   - Найдите приложение `neeno-caller` (ID: 11963388)

3. **Откройте сценарии**:
   - Кликните на приложение `neeno-caller`
   - Перейдите на вкладку **Scenarios**

4. **Создайте новый сценарий**:
   - Нажмите **Create Scenario**
   - Название: `ai_recruiter`
   - Описание: `AI-powered recruitment bot for Yango`
   - Нажмите **Create and Open in IDE**

5. **Скопируйте код сценария**:
   - Откройте файл на вашем компьютере:
     ```
     /Users/aostrikov/projects/neuro-caller/voximplant/recruitment_bot.js
     ```
   - Скопируйте **весь код** из файла
   - Вставьте в Cloud IDE (замените весь код там)
   - Нажмите **Save** (Ctrl+S или кнопка Save)

6. **Привяжите сценарий к правилу**:
   - Перейдите на вкладку **Rules**
   - Найдите ваше правило (ID: 3769281)
   - Убедитесь, что в поле **Scenario** выбран `ai_recruiter`
   - Если нет - выберите его и сохраните

---

### 2️⃣ Настроить OpenAI в Application Storage (2 минуты)

Запустите скрипт настройки:

```bash
cd /Users/aostrikov/projects/neuro-caller/voximplant
source ../venv/bin/activate
python vox_manager.py
```

Скрипт автоматически:
- Авторизуется в Voximplant
- Загрузит OpenAI API ключ
- Настроит бренд "Янго"
- Покажет статус

---

### 3️⃣ Проверить баланс Voximplant (1 минута)

1. В панели Voximplant → **Billing** → **Balance**
2. Убедитесь, что баланс > $0.50 для тестового звонка
3. Если нужно - пополните: **Add Funds** → минимум $10

---

### 4️⃣ Сделать тестовый звонок! 🎉

```bash
cd /Users/aostrikov/projects/neuro-caller/voximplant
source ../venv/bin/activate

# Тест подключения (без реального звонка)
python make_call_vox.py +79991234567 --test

# Реальный звонок на ваш номер
python make_call_vox.py +79991234567
```

Замените `+79991234567` на **ваш реальный номер телефона**.

---

## 🎯 Что произойдет при звонке:

1. Скрипт инициирует звонок через Voximplant API
2. Voximplant позвонит на указанный номер
3. При ответе - VoxEngine запустит сценарий `ai_recruiter`
4. Сценарий подключится к OpenAI Realtime API
5. AI рекрутер Анна поздоровается и начнет разговор о работе в Янго
6. Вы сможете разговаривать с AI в реальном времени

---

## 📊 Мониторинг

После звонка проверьте:

1. **Логи в Voximplant**:
   - В панели → **Logs**
   - Выберите приложение `neeno-caller`
   - Посмотрите детали звонка

2. **Статистика**:
   ```bash
   python make_call_vox.py +79991234567 --stats
   ```

---

## ❓ Возможные проблемы

### "Failed to authenticate"
- Проверьте API ключ в `.env`
- Убедитесь, что ключ активен в панели Voximplant

### "Failed to start call"
- Проверьте баланс
- Убедитесь, что Rule ID правильный
- Проверьте, что сценарий привязан к правилу

### "OpenAI connection failed"
- Проверьте OpenAI API ключ
- Запустите `python vox_manager.py` для настройки

### Нет звука при звонке
- Проверьте, что сценарий загружен в Cloud IDE
- Убедитесь, что OpenAI ключ настроен в Application Storage

---

## 📞 Быстрый старт (одной командой)

После загрузки сценария в Cloud IDE:

```bash
cd /Users/aostrikov/projects/neuro-caller/voximplant && \
source ../venv/bin/activate && \
python vox_manager.py && \
python make_call_vox.py +79991234567
```

---

## ✅ Checklist

- [ ] Сценарий загружен в Voximplant Cloud IDE
- [ ] Сценарий привязан к правилу (Rule ID: 3769281)
- [ ] Запущен `python vox_manager.py` для настройки OpenAI
- [ ] Баланс Voximplant > $0.50
- [ ] Сделан тестовый звонок

---

**Готово к работе!** 🎉

Первый звонок займет ~30 секунд для установки соединения с OpenAI. Последующие будут быстрее.