# desktop-2fa-watch — instrukcje dla współtwórców i agentów

## Współpraca i zakres zmian

- Wyjaśniaj decyzje i wyniki po polsku, prostym językiem. Zachowuj język i styl istniejącego kodu oraz dokumentacji.
- Przed większą zmianą przedstaw krótki plan, ryzyka i sposób sprawdzenia wyniku. Kontynuuj pracę w uzgodnionym zakresie bez dodatkowej rundy zatwierdzania planu.
- Wprowadzaj małe, celowe zmiany. Nie łącz poprawki z przebudową niezwiązanych modułów ani nie nadpisuj cudzych zmian.
- Podawaj uruchomione kontrole, ich wynik i ograniczenia. Nie deklaruj sukcesu testów, których nie uruchomiono, ani bezpieczeństwa na podstawie samych testów.

## Wspólny standard bezpieczeństwa 2FA

Te wymagania obowiązują także bez lokalnego, globalnego pliku Codexa. Przy zmianie wspólnego standardu porównaj instrukcje w desktop-2fa i wskaż potrzebne aktualizacje; osobne repozytoria nie synchronizują się automatycznie.

- Nigdy nie używaj rzeczywistych sekretów, haseł ani vaultów użytkownika w testach, logach, zgłoszeniach lub przykładach. Używaj jawnie syntetycznych danych. Nie dodawaj diagnostyki ujawniającej sekrety, klucze, URI `otpauth` lub wygenerowane kody.
- Używaj sprawdzonych bibliotek kryptograficznych i kryptograficznego generatora losowości. Zachowuj uwierzytelnione szyfrowanie, świeże sole i nonce; nie osłabiaj KDF, walidacji ani uwierzytelnienia dla wygody lub wydajności.
- Odrzucaj nieprawidłowe, uszkodzone i nieobsługiwane dane jawnie. Błąd odczytu, hasła lub uwierzytelnienia nie może powodować utworzenia pustego vaultu ani nadpisania danych.
- Przed zmianą formatu danych, parametrów kryptografii, publicznego API lub importu/eksportu sprawdź skutki dla istniejących użytkowników. Opisz wersjonowanie, zgodność, odzyskanie danych i migrację, jeśli jest potrzebna. Wspólny standard nie oznacza identycznego formatu przechowywania na obu platformach.
- Dla zmian kryptografii i przechowywania wymagaj testów regresji obejmujących błędne hasło, manipulację danymi, niepoprawne wejście i zachowanie danych przy błędach zapisu. Dla TOTP używaj wektorów RFC 6238 i kontrolowanego czasu, w tym granic okresów.
- Zachowuj działanie offline. Dodanie transmisji sekretów lub innego ruchu sieciowego wymaga jawnego zakresu zadania oraz analizy zagrożeń.
- Opisuj rzeczywiste zabezpieczenia i ograniczenia. Nie obiecuj audytu, certyfikacji ani gwarantowanego usuwania sekretów z pamięci.

## Kotlin, Wear OS i dane lokalne

- Projekt ma moduł `:app`, interfejs Compose i źródła w `app/src/main/java/org/desktop2fa/desktop/watch/`; testy JVM są w `app/src/test/`. Konfiguracja SDK i zależności jest w `app/build.gradle.kts` oraz katalogu `gradle/`; CI używa JDK 17.
- Przed zmianami ochrony danych przeczytaj `docs/SECURITY.md`, `docs/crypto.md` i `docs/compatibility.md`; polityka zgłoszeń jest w `SECURITY.md`. Dokumentacja odróżnia obecne ograniczenia MVP od wymagań docelowych poniżej. Nie rozszerzaj zadania automatycznie o naprawę wszystkich znanych ograniczeń.
- Obecny vault D2FA v1 używa Argon2id i AES-256-GCM z hasłem użytkownika. Keystore chroni klucz preferencji funkcji „Remember on watch”; nie zastępuje hasła vaultu. Nie zmieniaj tego rozdziału bez analizy zgodności i odzyskiwania danych. Zgodność między aplikacjami oceniaj według `docs/compatibility.md` i testów, a nie samego nagłówka D2FA.
- Najpierw sprawdź rzeczywistą strukturę modułów, Gradle Wrapper, konfigurację SDK i CI. Nie zakładaj konkretnej biblioteki UI, bazy danych ani dostępności zadania Gradle.
- Korzystaj z mechanizmów Android Keystore do ochrony lokalnych kluczy, odpowiednio do przyjętego modelu zagrożeń. Nie przechowuj sekretów jawnym tekstem w preferencjach, plikach, zasobach ani kodzie. Nie zakładaj dostępności sprzętowej ochrony kluczy na każdym zegarku.
- Sprawdzaj zachowanie przy utracie lub unieważnieniu klucza, blokadzie urządzenia i błędach odszyfrowania. Nie zastępuj nieczytelnych danych pustym magazynem; określ ścieżkę odzyskania lub świadomego resetu.
- Obejmij analizą backup Androida, transfer na inne urządzenie i eksport. Nie dopuszczaj do niezamierzonego kopiowania sekretów ani obiecuj odzyskania danych bez dostępnego klucza.
- Nie umieszczaj sekretów w stanie odtwarzanym przez system, argumentach nawigacji, Intentach ani powiadomieniach. Ograniczaj czas życia odszyfrowanych danych; JVM nie gwarantuje bezpiecznego wyzerowania wszystkich kopii.
- Używaj współbieżności strukturalnej i zakresów coroutine związanych z lifecycle. KDF i I/O wykonuj poza wątkiem UI; anulowanie nie może pozostawić częściowego zapisu.
- Odświeżaj kody zgodnie z czasem i lifecycle ekranu. Unikaj aktywnych pętli, zbędnych wake locków i pracy w tle; uwzględnij ambient mode, wygaszenie ekranu, odtworzenie procesu oraz zmianę czasu systemowego.
- Zachowuj algorytm, liczbę cyfr i okres TOTP. Jeśli istnieje wymiana danych z desktop-2fa, testuj ją wspólnymi syntetycznymi wektorami; nie zakładaj zgodności binarnych vaultów.
- Uwzględniaj mały i okrągły ekran, czytelność, dostępność oraz ograniczenia interakcji zegarka.

## Weryfikacja

- Na Windows uruchamiaj z katalogu głównego polecenia odpowiadające obecnemu CI:

```powershell
.\gradlew.bat :app:testDebugUnitTest --stacktrace
.\gradlew.bat :app:assembleDebug --stacktrace
```

- Używaj Gradle Wrapper z repozytorium. Dobierz zadania testów, lintowania i budowania na podstawie istniejących modułów i CI; raportuj dokładne polecenia i wyniki.
- Dla zmian ochrony danych uruchom testy kryptografii, magazynu, błędów zapisu i zgodności. Dla TOTP sprawdź wektory RFC 6238 i granice okresów.
- Zachowania Android Keystore, lifecycle, ambient mode i odtwarzania procesu sprawdzaj odpowiednimi testami instrumentacyjnymi lub na urządzeniu/emulatorze. Wynik testów JVM nie zastępuje tych kontroli.
- Przy zmianach zachowania aktualizuj dokumentację użytkownika i bezpieczeństwa oraz changelog, jeśli istnieją. Jawnie zgłoś brak SDK, urządzenia lub innej wymaganej możliwości weryfikacji.
- Raporty w `docs/testing/README.md` opisują wcześniejsze kontrole UI i ich ograniczenia; nie są wynikiem testów bieżącej zmiany. Dla zmian wyłącznie instrukcji wystarczy przegląd treści, ścieżek i białych znaków.
