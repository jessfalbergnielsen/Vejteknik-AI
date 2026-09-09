# Vejteknik-AI

Python-værktøj til at læse dokumenter i et lukket lokalt miljø og returnere ord, sætninger og deres placering i filer.

## Funktioner

- Scanner lokale `.txt`- og `.pdf`-filer rekursivt i en mappe
- Returnerer både enkelte ord og hele sætninger
- Viser hvor teksten blev fundet: fil, side (for PDF), linje og kolonne
- Kan filtrere resultater med en søgetekst
- Kan udskrive som læsbar tekst eller JSON

## Installation

```bash
python -m pip install -r requirements.txt
```

## Brug

```bash
python document_search.py /sti/til/mappe
```

Kun ord:

```bash
python document_search.py /sti/til/mappe --kind words
```

Kun sætninger som indeholder et bestemt ord:

```bash
python document_search.py /sti/til/mappe --kind sentences --contains vej
```

JSON-output:

```bash
python document_search.py /sti/til/mappe --json
```

## Test

```bash
python -m unittest discover -s tests
```
