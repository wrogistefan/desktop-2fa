# desktop-2fa — instrukcje dla współtwórców i agentów

## Współpraca i zakres zmian

- Wyjaśniaj decyzje i wyniki po polsku, prostym językiem. Zachowuj język i styl istniejącego kodu oraz dokumentacji.
- Przed większą zmianą przedstaw krótki plan, ryzyka i sposób sprawdzenia wyniku. Kontynuuj pracę w uzgodnionym zakresie bez dodatkowej rundy zatwierdzania planu.
- Wprowadzaj małe, celowe zmiany. Nie łącz poprawki z przebudową niezwiązanych modułów ani nie nadpisuj cudzych zmian.
- Podawaj uruchomione kontrole, ich wynik i ograniczenia. Nie deklaruj sukcesu testów, których nie uruchomiono, ani bezpieczeństwa na podstawie samych testów.

## Wspólny standard bezpieczeństwa 2FA

Te wymagania obowiązują także bez lokalnego, globalnego pliku Codexa. Przy zmianie wspólnego standardu porównaj instrukcje w desktop-2fa-watch i wskaż potrzebne aktualizacje; osobne repozytoria nie synchronizują się automatycznie.

- Nigdy nie używaj rzeczywistych sekretów, haseł ani vaultów użytkownika w testach, logach, zgłoszeniach lub przykładach. Używaj jawnie syntetycznych danych. Nie dodawaj diagnostyki ujawniającej sekrety, klucze, URI `otpauth` lub wygenerowane kody.
- Używaj sprawdzonych bibliotek kryptograficznych i kryptograficznego generatora losowości. Zachowuj uwierzytelnione szyfrowanie, świeże sole i nonce; nie osłabiaj KDF, walidacji ani uwierzytelnienia dla wygody lub wydajności.
- Odrzucaj nieprawidłowe, uszkodzone i nieobsługiwane dane jawnie. Błąd odczytu, hasła lub uwierzytelnienia nie może powodować utworzenia pustego vaultu ani nadpisania danych.
- Przed zmianą formatu danych, parametrów kryptografii, publicznego API lub importu/eksportu sprawdź skutki dla istniejących użytkowników. Opisz wersjonowanie, zgodność, odzyskanie danych i migrację, jeśli jest potrzebna. Wspólny standard nie oznacza identycznego formatu przechowywania na obu platformach.
- Dla zmian kryptografii i przechowywania wymagaj testów regresji obejmujących błędne hasło, manipulację danymi, niepoprawne wejście i zachowanie danych przy błędach zapisu. Dla TOTP używaj wektorów RFC 6238 i kontrolowanego czasu, w tym granic okresów.
- Zachowuj działanie offline. Dodanie transmisji sekretów lub innego ruchu sieciowego wymaga jawnego zakresu zadania oraz analizy zagrożeń.
- Opisuj rzeczywiste zabezpieczenia i ograniczenia. Nie obiecuj audytu, certyfikacji ani gwarantowanego usuwania sekretów z pamięci.

## Python, vault i interfejsy

- Źródła: `src/desktop_2fa/`; testy: `tests/`. CLI używa Typer, a obecny interfejs jest prototypem Textual. Nie zakładaj istnienia pełnego GUI.
- Wymagana wersja Pythona i narzędzia są określone w `pyproject.toml`. Zachowuj zgodność runtime z Pythonem >=3.11; konfiguracja lintera nie upoważnia do używania składni niedostępnej w minimalnej wersji.
- Model bezpieczeństwa opisują `docs/SECURITY.md` i `docs/crypto.md`; politykę bezpieczeństwa opisuje `SECURITY.md`. Przy zmianie zachowania aktualizuj właściwe dokumenty, instrukcję użytkownika i `CHANGELOG.md`.
- Obecny vault używa Argon2id i AES-256-GCM. Zachowuj wymaganie jawnego, niepustego hasła, walidację modelu oraz ograniczenia rozmiaru i typu pliku.
- Zachowuj zapis przez plik tymczasowy i zastąpienie docelowego pliku. Testuj błędy I/O bez korzystania z domyślnego vaultu użytkownika; używaj katalogów tymczasowych.
- Zgodność historyczna ma granice opisane w `tests/fixtures/vaults/README.md`. Binarne fixture'y są niezmiennymi danymi wejściowymi; nie regeneruj ich bieżącym writerem, aby uciszyć regresję. Nie deklaruj wsparcia dla formatów jawnie nieobsługiwanych.
- Sprawdzaj wpływ na API `Vault`, wyjątki, kody wyjścia CLI, wybór ścieżki vaultu i rozstrzyganie nazw wpisów. Zachowuj parametry TOTP podczas importu i zapisu; nie wybieraj arbitralnie wpisu przy niejednoznaczności.
- Nie wykonuj ciężkiego KDF ani I/O w sposób blokujący interfejs. Ograniczaj czas przechowywania hasła i odszyfrowanych danych; Python nie gwarantuje ich bezpiecznego wyzerowania.

## Weryfikacja

Używaj istniejącego środowiska wirtualnego. Na Windows uruchamiaj polecenia z katalogu głównego repozytorium:

```powershell
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe -m ruff check .
.venv/Scripts/python.exe -m black --check .
.venv/Scripts/python.exe -m mypy src
```

Dobieraj kontrole do zmiany: przy zmianach kodu uruchom odpowiednie testy i kontrole jakości; przy zmianach vaultu, kryptografii lub TOTP także pełny zestaw testów. Dla samych instrukcji wystarczy przegląd treści, ścieżek i `git diff --check`. CI jest opisane w `.github/workflows/`; lokalny wynik na Windows nie potwierdza wyniku na macOS ani Linux.
