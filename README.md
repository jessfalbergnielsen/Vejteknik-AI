# Vejteknik-AI
AI til sagsbehandling af vejprojekt sager ved politiet

## Dokumentsøgning i lukket filgruppe

Repositoryet indeholder nu et lille søgeværktøj, som kun arbejder inden for en angivet mappe og kan søge efter ord eller sætninger i:

- `.txt`
- `.pdf`
- `.doc`
- `.docx`

Resultaterne viser:

- præcis fil
- sidenummer for PDF
- linjenummer for TXT/PDF/DOC
- afsnitsnummer for DOCX
- tegnposition for selve fundet
- et kort uddrag af teksten

### Installation

```bash
python -m pip install -r requirements.txt
```

For `.doc` kræves desuden et systemværktøj som `antiword` eller `catdoc`.

### Brug

```bash
python document_search.py /sti/til/lukket_filgruppe --query "vejbredde"
python document_search.py /sti/til/lukket_filgruppe --query "vejlov" --query "sagsbehandling" --json
```
