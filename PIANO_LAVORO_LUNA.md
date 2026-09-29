# Piano di lavoro per Luna — Solver Turni

## Obiettivo e perimetro

Correggere i 15 problemi individuati nella revisione del programma, mantenendo Python, Streamlit, OR-Tools e Supabase. Consegnare codice, migrazioni, test e istruzioni riproducibili. Non riscrivere l'applicazione e non introdurre servizi aggiuntivi se non necessari.

Questo documento è un piano: non autorizza da solo modifiche al database di produzione, pubblicazioni o cancellazioni di dati. Quando viene assegnata l'implementazione, completare autonomamente il lavoro locale e preparare gli interventi esterni in forma revisionabile.

Lavorare per fasi nell'ordine indicato. Prima di ogni fase rileggere i file coinvolti e preservare eventuali modifiche dell'utente. Non delegare ad altri agenti salvo richiesta esplicita. Non visualizzare o riportare credenziali nei log e nei resoconti.

## Riscontri da cui partire

- `src/engine/solver.py` crea variabili anche per tutte le assenze, senza vietarle in mancanza di richieste, e conserva un riferimento al dizionario globale dei turni.
- `src/engine/constraints.py` vieta N → mattina, ma non impone N → smonto; vieta sempre lo smonto al primo giorno e tratta le preferenze come obblighi.
- `src/ui/view_admin.py` genera senza leggere il calendario esistente e salva una cella alla volta, senza rispettare `is_locked`.
- `src/engine/objectives.py` conta le assenze nei festivi, mentre `src/utils/exporter.py` le esclude; l'export pubblico riceve già i codici mascherati come `ASS`.
- `src/ui/view_roster.py` non implementa il salvataggio manuale e usa il nome come chiave; anche le selezioni di dipendenti e richieste hanno problemi con gli omonimi.
- `src/main.py` autentica con una password condivisa e mantiene sessioni admin separate per pagina; le policy SQL presuppongono invece utenti Supabase autenticati.
- `EmployeeRepository.get_all_employees()` restituisce soltanto gli attivi, anche quando serve visualizzare lo storico.
- Molti file di test sono vuoti; `test_smonto_consistency` non verifica nulla; `test_repository_roster.py` può sovrascrivere un turno di un dipendente reale.
- `test_precision.py` modifica indirettamente `SHIFT_DEFINITIONS`, contaminando potenzialmente gli altri test.

Questi riscontri derivano dal codice locale: configurazione e policy effettivamente installate su Supabase non sono state verificate.

## Decisioni da chiarire durante l'avvio

Raccogliere le risposte necessarie mentre si procede con test, identificativi, calcoli condivisi e persistenza; non fermare il lavoro indipendente.

1. **Riposi:** confermare se dopo N siano obbligatori S e poi R, quante notti consecutive siano consentite e quali limiti orari e sequenze vadano applicati. La sequenza ideale 1 → K → N → S → R oggi è solo un obiettivo, non prova di una regola obbligatoria.
2. **Ore contrattuali:** confermare la regola attuale di 6 ore per giorno esclusi domeniche e festivi, il trattamento delle assenze e la modalità di calcolo del part-time.
3. **Accesso:** definire chi possa vedere il calendario, esportare dati e consultare totali individuali, conservando solo gli accessi pubblici esplicitamente voluti.
4. **Assenze manuali:** stabilire se debbano creare una richiesta approvata o rappresentare un'eccezione autorizzata e tracciata.

Non inventare norme contrattuali o dichiarare conformità normativa. Implementare regole configurabili, documentare quelle confermate e impedire la pubblicazione quando manca una configurazione indispensabile. Per un'eventuale verifica normativa usare fonti ufficiali aggiornate.

## Fase 0 — Mettere in sicurezza le verifiche

**File:** `tests/`, `test_holiday_logic.py`, `requirements.txt`, configurazione pytest e README.

- Identificare l'interprete e l'ambiente virtuale realmente utilizzati, senza reinstallare dipendenze inutilmente.
- Ispezionare i test prima di lanciare l'intera suite: separare quelli locali da quelli che accedono a Supabase.
- Rendere i test di integrazione esclusi per impostazione predefinita e attivabili soltanto con configurazione esplicita di un database di test.
- Eliminare l'uso del primo dipendente disponibile nei test: usare fixture dedicate con identificativi unici e pulire solo i record creati dal test.
- Usare mock del repository per i test locali; nessuna connessione al database deve avvenire durante la raccolta dei test.
- Isolare le definizioni dei turni per istanza del solver, così un test non modifica le istanze successive.
- Registrare il risultato iniziale dei test locali e distinguere errori preesistenti da regressioni introdotte.

**Criterio di completamento:** la suite locale gira senza segreti o rete e non può modificare dati reali; documentato un comando separato per l'integrazione.

## Fase 1 — Centralizzare regole, identità e calcolo delle ore

**File:** `src/models/employee.py`, `src/models/shift.py`, `src/utils/holidays.py`, `src/engine/objectives.py`, `src/utils/exporter.py`; nuovi moduli di dominio solo dove utili.

- Introdurre una configurazione validata per coperture per ruolo, capacità, ciclo e ancoraggio, riposi, penalità e limite di calcolo.
- Mantenere i valori esistenti come default per le impostazioni già definite; non trasformare automaticamente il ciclo ideale in un vincolo obbligatorio.
- Usare gli stessi dati di configurazione nel solver, nella verifica del calendario e nell'interfaccia.
- Definire una funzione condivisa per le ore accreditate al dipendente in una data, distinguendole dalle ore effettivamente lavorate per i vincoli di riposo.
- Definire un unico calcolo del target contrattuale, con percentuale part-time o override esplicito senza doppia riduzione.
- Conservare una rappresentazione numerica esatta compatibile con CP-SAT, per esempio centesimi d'ora, con conversione e arrotondamento documentati.
- Usare sempre ID come chiave interna; mostrare nome e matricola come etichetta. Non usare il nome come identificativo nemmeno nei DataFrame o nell'export.
- Calcolare i totali dai dati originali lato server, applicando la mascheratura soltanto alla rappresentazione destinata all'utente.

**Verifiche:** 7,25 ore rimangono esatte; solver e report producono gli stessi totali nei giorni ordinari e festivi; il part-time modifica coerentemente il target; due omonimi restano distinti.

## Fase 2 — Correggere assenze, richieste e turni bloccati

**File:** `src/engine/solver.py`, `src/engine/constraints.py`, `src/database/repository.py`, `src/ui/view_requests.py`, `src/ui/view_admin.py`.

- Normalizzare tipi e stati delle richieste, gestendo esplicitamente i dati legacy `Approvato` e `APPROVED`; il solver deve usare soltanto richieste approvate.
- Vietare F, M, 104 e P su ogni coppia dipendente/data priva di una corrispondente assenza approvata o eccezione manuale autorizzata.
- Applicare le assenze approvate come obblighi; trasformare le preferenze di turno in penalità configurabili e riportare quelle non soddisfatte.
- Validare intervalli invertiti, codici sconosciuti, dipendenti mancanti e richieste sovrapposte prima di costruire il modello.
- Non considerare un duplicato identico come due obblighi diversi: consolidarlo o segnalarlo chiaramente; bloccare le assenze obbligatorie incompatibili.
- Leggere i turni esistenti del periodo e imporre i valori delle celle bloccate al solver; una richiesta incompatibile con un blocco produce un errore spiegato.
- Conservare i flag di blocco al salvataggio ed evitare che una rigenerazione li azzeri implicitamente.

**Verifiche:** nessuna assenza nasce spontaneamente; una preferenza impossibile non rende impossibile il calendario; richieste non approvate non vincolano; un turno bloccato resta invariato e i conflitti vengono identificati.

## Fase 3 — Riposi e continuità tra mesi

**File:** `src/engine/constraints.py`, `src/engine/solver.py`, repository e servizio di validazione del calendario.

- Passare al solver il contesto dei giorni esterni al periodo: la finestra deve essere sufficiente per le regole configurate, non sempre limitata a un giorno.
- Leggere lo storico precedente e verificare anche la compatibilità con eventuali turni già salvati dopo la fine del periodo.
- Consentire lo smonto iniziale quando giustificato dal turno precedente; distinguere storico assente da giorno di riposo noto.
- Applicare le sequenze obbligatorie e i limiti confermati, comprese eventuali finestre di riposo e massimi di lavoro consecutivo.
- Gestire esplicitamente un contesto iniziale incompleto: richiederne l'inserimento o la conferma, senza inventare turni passati.
- Se il periodo successivo non è ancora pianificato, rendere visibili gli obblighi che derivano dagli ultimi turni e applicarli alla generazione successiva.
- Riutilizzare le medesime regole per verificare le modifiche manuali; non mantenere due definizioni divergenti del calendario valido.

**Verifiche:** notte a fine mese e smonto a inizio mese; cambio anno e febbraio bisestile; conflitto con il mese successivo; storico mancante; violazioni delle regole sui riposi confermate.

## Fase 4 — Salvataggio atomico e modifiche manuali

**File:** `src/database/repository.py`, `src/ui/view_admin.py`, `src/ui/view_roster.py`, migrazioni SQL e servizio applicativo del calendario.

- Separare il calcolo dalla pubblicazione: conservare una bozza in sessione, mostrarne differenze, avvisi e preferenze non soddisfatte, quindi consentire il salvataggio esplicito.
- Implementare un'operazione transazionale lato database, per esempio una funzione RPC PostgreSQL: il mese deve essere aggiornato integralmente oppure restare invariato.
- Evitare di chiamare «atomico» un ciclo di richieste HTTP o una sequenza di batch indipendenti.
- Limitare ogni salvataggio al periodo e ai dipendenti interessati, preservando record storici e dati estranei alla bozza.
- Introdurre un controllo di revisione concorrente: se il calendario è cambiato dopo la lettura, rifiutare la sovrascrittura e chiedere di ricaricare.
- Proteggere nella transazione anche i blocchi correnti e le precondizioni rilevanti: una bozza non deve ignorare richieste o regole cambiate nel frattempo.
- Nell'editor offrire codici turno validi, mantenere gli ID non modificabili e implementare il salvataggio delle differenze.
- Validare l'intero calendario risultante, comprese le date adiacenti, prima di salvare modifiche manuali; sbloccare una cella deve essere un'azione esplicita.
- Tracciare autore, data, origine dell'operazione e valori modificati nello stesso salvataggio; usare l'identità autenticata, senza accettare un autore arbitrario dal client.

**Verifiche:** un errore intermedio non lascia scritture parziali; due editor concorrenti non si sovrascrivono; una modifica valida persiste e una non valida mostra cella e motivo; i blocchi sono preservati anche in caso di concorrenza.

## Fase 5 — Autenticazione, autorizzazioni e privacy

**File:** `src/main.py`, `src/database/client.py`, repository, `database/security.sql`, `database/policies_update.sql`, migrazioni e documentazione.

- Implementare identità individuali e ruoli coerenti tra applicazione e Supabase, con una sessione unica e logout globale per tutte le pagine.
- Non memorizzare un client autenticato mutabile nella cache globale condivisa: isolare credenziali e sessioni di ciascun utente.
- Collegare gli utenti applicativi ai dipendenti con una relazione esplicita, senza assumere che `auth.uid()` coincida con l'ID del dipendente.
- Sostituire le email segnaposto nelle policy con una gestione esplicita dei ruoli e impedire agli utenti di attribuirsi privilegi.
- Applicare i permessi anche nel database e nelle RPC: nascondere un bottone nell'interfaccia non costituisce autorizzazione.
- Definire separatamente accesso al calendario, anagrafiche, richieste e log; evitare di distribuire la chiave service-role ai client.
- Esporre a lettori non amministrativi solo i dati previsti, usando viste o funzioni con permessi verificati; RLS da sola non maschera singole colonne.
- Verificare che esportazioni, errori e metadati non espongano M, 104, note o altri dettagli riservati; mostrare i totali soltanto ai ruoli autorizzati.
- Se è prevista una lettura anonima, implementarla soltanto sulla rappresentazione consentita, mantenendo protette le tabelle originali.

**Verifiche:** matrice di accesso per anonimo, lettore e amministratore; tentativi diretti di scrittura respinti; nessuno scambio di sessioni tra utenti; logout effettivo ovunque; assenze riservate protette anche nell'Excel.

## Fase 6 — Storico, configurazione ed equità

**File:** `src/database/repository.py`, `src/ui/state.py`, `src/ui/view_employees.py`, `src/ui/view_roster.py`, `src/engine/objectives.py`, modelli e migrazioni.

- Distinguere la ricerca dei dipendenti attivi per generare nuovi turni dalla ricerca dei dipendenti referenziati nei calendari storici.
- Preferire la disattivazione per uscita dal servizio; impedire cancellazioni che compromettano turni, richieste o tracciabilità esistenti.
- Conservare il contesto contrattuale necessario a leggere lo storico senza ricalcolarlo con il part-time o le regole correnti, usando dati con decorrenza o snapshot adeguati.
- Rendere modificabili e persistenti le impostazioni introdotte nella fase 1, con validazione e decorrenza/versione quando influenzano calendari già salvati.
- Invalidare o aggiornare la cache dopo modifiche pertinenti e rilevare dati obsoleti prima della generazione o del salvataggio.
- Aggiungere obiettivi di equilibrio per notti e festivi, rapportati a part-time, disponibilità e limitazioni; non penalizzare un esente notte per non aver svolto notti.
- Usare pesi comprensibili e configurabili: i vincoli obbligatori rimangono tali e non si sacrificano per migliorare un punteggio.
- Mostrare indicatori sintetici per dipendente: ore, scostamento dal target, notti, festivi e preferenze soddisfatte, nei limiti dei permessi.

**Verifiche:** un dipendente disattivato resta nello storico ma non nei nuovi turni; cambiare contratto non altera i report passati; due omonimi rimangono distinti in ogni vista; equità valutata su fixture realistiche.

## Fase 7 — Diagnostica e verifica completa

**File:** `src/engine/solver.py`, `src/ui/view_admin.py`, `tests/`, README e migrazioni.

- Distinguere OPTIMAL, FEASIBLE, INFEASIBLE, UNKNOWN e MODEL_INVALID senza presentarli tutti come «nessuna soluzione».
- Per una soluzione FEASIBLE mostrare che è valida ma non necessariamente ottima; per UNKNOWN spiegare che non è stata determinata la fattibilità entro i limiti.
- Aggiungere controlli preliminari su personale disponibile per ruolo, richieste e blocchi; presentarli come controlli necessari, non come prova generale di fattibilità.
- Identificare i conflitti con regole, dipendenti e date; se si usano assumptions di CP-SAT, descrivere il risultato come insieme sufficiente di vincoli in conflitto, non necessariamente minimo.
- Non disattivare automaticamente coperture, assenze o riposi per ottenere una soluzione.
- Completare i test oggi vuoti con casi comportamentali delle fasi precedenti; sostituire stampe e `pass` con asserzioni.
- Aggiungere un flusso completo su dati sintetici: anagrafica → richieste → generazione → bozza → pubblicazione → modifica → esportazione.
- Verificare migrazioni e RPC su database isolato, includendo rollback della transazione, concorrenza e autorizzazioni; i mock da soli non bastano per questi aspetti.
- Misurare un mese con organico realistico e riportare durata, stato e qualità della soluzione senza promettere tempi non verificati.

**Criterio di completamento:** test locali superati; test di integrazione superati in ambiente isolato oppure esplicitamente elencati come non verificati con causa; nessuna dichiarazione di successo su controlli non eseguiti.

## Migrazioni e consegna

- Preparare migrazioni numerate e non distruttive: il solo `database/schema.sql` attuale non contiene tutte le modifiche attese dal codice.
- Verificare sia l'installazione nuova sia l'aggiornamento dei dati esistenti; normalizzare stati e tipi senza cancellare silenziosamente valori sconosciuti.
- Documentare ordine di esecuzione, prerequisiti, controlli dopo l'aggiornamento e procedura di recupero prima di proporre l'applicazione a un database reale.
- Aggiornare il README con avvio, configurazione senza segreti reali, ruoli, regole confermate, test locali e integrazione.
- Consegnare un riepilogo con file modificati, test e risultati, eventuali decisioni ancora mancanti e operazioni esterne ancora da applicare.
- Non indicare «completato» se una funzione è solo simulata, una migrazione necessaria non è stata verificata o restano regole indispensabili non definite.

## Tracciabilità dei 15 punti della revisione

| Punto | Risultato richiesto | Fasi |
|---|---|---|
| 1 | Assenze solo se autorizzate | 2 |
| 2 | Riposi obbligatori configurati e verificati | 1, 3 |
| 3 | Continuità tra mesi e gestione del contesto | 3 |
| 4 | Blocchi rispettati dal solver e dal salvataggio | 2, 4 |
| 5 | Unico calcolo delle ore | 1 |
| 6 | Totali corretti anche con assenze mascherate | 1, 5 |
| 7 | Pubblicazione atomica e controllo concorrenza | 4 |
| 8 | Modifiche manuali effettivamente salvabili | 4 |
| 9 | Omonimi distinguibili tramite ID e matricola | 1, 6 |
| 10 | Preferenze flessibili con esito consultabile | 2 |
| 11 | Conflitti spiegati e stati solver distinti | 2, 7 |
| 12 | Autenticazione e permessi coerenti | 5 |
| 13 | Configurazione, part-time ed equità | 1, 6 |
| 14 | Storico visibile per dipendenti disattivati | 6 |
| 15 | Test effettivi, sicuri e riproducibili | 0–7 |

## Istruzione pronta da assegnare a Luna

> Implementa il piano in `PIANO_LAVORO_LUNA.md` seguendo l'ordine delle fasi. Parti dall'isolamento dei test che oggi possono accedere al database reale. Raccogli presto le decisioni di dominio indispensabili e prosegui intanto con il lavoro indipendente. Per ogni fase realizza le modifiche, esegui le verifiche pertinenti e annota l'esito. Preserva i dati e le modifiche esistenti, non introdurre regole contrattuali arbitrarie e non applicare migrazioni in produzione senza autorizzazione. Porta a termine tutto il lavoro locale eseguibile e consegna un resoconto verificabile, indicando chiaramente eventuali dipendenze esterne ancora aperte.
