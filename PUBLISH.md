# Как залить проект на GitHub — пошагово

Инструкция для случая «до этого с git не работал». Все команды выполняются
в cmd внутри папки проекта:

```cmd
cd C:\путь\к\tg-msg
```

## Шаг 0. Установи git (если ещё нет)

Скачай с <https://git-scm.com/download/win>, при установке везде жми Next.
Проверь:

```cmd
git --version
```

Один раз представься (имя и почта попадут в историю коммитов):

```cmd
git config --global user.name "rezonator"
git config --global user.email "твоя@почта.ru"
```

## Шаг 1. Создай репозиторий на сайте

1. Зайди на <https://github.com/new> (зарегистрируйся, если нет аккаунта).
2. Repository name: `tg-msg`
3. Описание: `Спамер в активное поле ввода: CLI-утилита с мастером настройки, пресетами скорости и памятью настроек`
4. Публичный (Public). **Не** добавляй README/License галочками — они уже есть в проекте.
5. Create repository. GitHub покажет команды — они совпадают с шагом 2.

## Шаг 2. Запушь проект

```cmd
git init
git add .
git commit -m "TG-MSG v1.1.0: мастер настройки, пресеты скорости, новый дизайн"
git branch -M main
git remote add origin https://github.com/sokolovdencik494-hash/tg-msg.git
git push -u origin main
```

При первом push откроется окно GitHub — войди через браузер.

## Шаг 3. Включи сайт (GitHub Pages)

Сайт лежит в папке `docs/` — GitHub Pages умеет публиковать её напрямую:

1. В репозитории: **Settings → Pages** (слева в меню).
2. **Source**: `Deploy from a branch`.
3. **Branch**: `main`, папка: `/docs`. Save.
4. Через минуту сайт будет жить по адресу
   `https://sokolovdencik494-hash.github.io/tg-msg/`

Ссылку на сайт добавь в описание репозитория (About — кнопка справа сверху).

## Шаг 4. Причешись

- В **About** репозитория добавь topics: `python`, `cli`, `telegram`, `automation`, `typer`
- Проверь, что README красиво отрисовался, бейджи загрузились
- Сделай релиз: **Releases → Create a new release** → тег `v1.1.0` →
  в описание скопируй секцию 1.1.0 из CHANGELOG.md
- (Опционально) прикрепи к релизу `tgmsg.exe` из `dist/` — тогда скачка в один клик

## Обновления в будущем

```cmd
git add .
git commit -m "что изменил"
git push
```

## Если что-то пошло не так

| Проблема | Решение |
|---|---|
| `remote origin already exists` | `git remote set-url origin https://github.com/sokolovdencik494-hash/tg-msg.git` |
| Просит логин-пароль и отвергает | Пароли не работают, нужен токен: GitHub → Settings → Developer settings → Personal access tokens, либо вход через окно браузера |
| Запушил лишнее (например, `dist/`) | Он в `.gitignore`, но если успел: `git rm -r --cached dist` и снова `git commit` + `push` |
| `main` vs `master` | `git branch -M main` переименует текущую ветку |

## Шаг 5. Настрой профиль GitHub

Профиль — это лицо. Настройка на полминуты (правка профиля:
страница профиля → карандаш у аватара, или <https://github.com/settings/profile>):

| Поле | Что вписать |
|---|---|
| Имя | `rezonator` — так тебя будут видеть |
| Биография | `Делаю CLI-утилиты на Python. Автор TG-MSG` |
| Местоположение | по желанию, можно не указывать |
| Веб-сайт | после включения Pages: `https://sokolovdencik494-hash.github.io/tg-msg/` |
| Соцсети | по желанию |

**Аватар.** Кликни по круглой картинке профиля (на ней есть кнопка со смайликом),
выбери «Upload new picture» и загрузи файл аватара. Квадратная картинка
от 500×500 px смотрится лучше всего.

**Прикрепи репозиторий.** На вкладке «Pinned» (Закреплённые) нажми
«Customize your pins» и закрепи `tg-msg` — он будет виден прямо в профиле.
