---
name: product-manager
description: Utilizza questa skill per creare e gestire il prodotto, definendo la visione, le personas, i user stories e i requisiti funzionali.
---

# PRODUCT_MANAGER.MD

1. Visione del Prodotto

Nome: OpenShift Scheduler (OSS-Manager)
Vision: Liberare i coordinatori infermieristici dall'incubo dei fogli Excel e dei calcoli manuali, garantendo turni equi, legali e trasparenti con un solo click.
Core Value: "Automazione Intelligente, Controllo Umano". L'algoritmo fa il lavoro sporco (matematica e incastri), l'Admin prende le decisioni finali.
2. Personas (Utenti Tipo)
A. Elena, la Coordinatrice (Admin)

    Obiettivo: Chiudere il turno del mese successivo in meno di 30 minuti (oggi ci mette 2 giorni).

    Pain Points: Errori di distrazione (es. doppio turno), calcolo manuale delle ore, lamentele per "favoritismi" percepiti.

    Cosa vuole: Un tasto "Genera", la certezza che le regole legali (11h riposo) siano rispettate, e la libertà di cambiare manualmente una casella se serve, vedendo subito l'impatto sul monte ore.

B. Marco, l'Infermiere/OSS (Observer)

    Obiettivo: Sapere quando lavora per organizzare la vita privata.

    Pain Points: Turni pubblicati in ritardo, turni massacranti (troppe notti vicine), non sapere con chi è in turno.

    Cosa vuole: Aprire un link dal telefono, vedere il tabellone completo (chi c'è con me?), vedere che le sue ferie sono state rispettate.

3. User Stories & Requisiti Funzionali
Epic 1: Configurazione & Vincoli (Input)

    US 1.1 - Gestione Staff & Triplette: Come Admin, voglio assegnare ogni dipendente a una "Tripletta" (Squadra A, B, C...) in modo che l'algoritmo sappia qual è il suo "ciclo naturale" (1-K-N-S-R).

    US 1.2 - Assenze: Come Admin, inserisco Ferie, Malattie e 104 prima di generare il turno.

        Regola: Le Malattie/104 sono inamovibili. Le Ferie sono "sacrificabili" dall'algoritmo (con altissima penalità) solo se è l'unico modo per coprire il servizio minimo.

Epic 2: Il Motore di Generazione (Core)

    US 2.1 - Copertura Minima (Hard Constraint): Il sistema non deve mai proporre un turno con meno personale del minimo stabilito (es. < 2 Inf notte), a meno che non manchino fisicamente dipendenti (in quel caso: Alert).

    US 2.2 - Obiettivo Orario Mensile: Il sistema deve assegnare turni extra o riposi per portare il saldo ore del dipendente nel range Target ±5h.

        Logica: Se Tizio è in debito, rompi la "Tripletta" e dagli una mattina in più. Se è in credito, dagli un riposo in più.

        Reset: Il saldo si calcola solo sul mese corrente. Non c'è riporto dal mese precedente.

    US 2.3 - La Matrice Ideale: Se non ci sono esigenze di copertura o di ore, il sistema deve seguire pedissequamente la sequenza della Tripletta (1-K-N-S-R).

Epic 3: Gestione & Pubblicazione (Output)

    US 3.1 - La Griglia Interattiva: Come Admin, vedo il risultato come un foglio Excel colorato.

    US 3.2 - Modifica "God Mode": Come Admin, posso cliccare su una cella e forzare un turno manualmente.

        Feedback: Se la mia modifica viola un vincolo (es. metto Mattina dopo Notte), il sistema mi mostra un warning rosso ma mi lascia salvare (l'ultima parola è umana).

    US 3.3 - Visualizzazione Pubblica: Come Observer, accedo in sola lettura e vedo l'intera matrice del reparto (righe=colleghi, colonne=giorni).

4. Logica di Business (Dettaglio Ore)
Calcolo Target Mensile

Il "Target" per ogni dipendente è dinamico:
Target=(GiorniNelMese−DomenicheEfestivi)×6.0
Calcolo Saldo Effettivo
Saldo=(∑OreLavorate+∑OreAssenzaRetribuita)−Target

    Ore Lavorate: Mattina=7, Pom=7, Notte=10.

    Ore Assenza Retribuita: Ferie/Permessi/Malattia/104 = 6h (standard giornaliero).

    Obiettivo Algoritmo: Minimizzare il valore assoluto del Saldo (∣Saldo∣→0).

    Tolleranza: Accettabile un saldo finale tra -5h e +5h.

5. Roadmap MVP (Minimum Viable Product)

Questa è la lista delle funzionalità strettamente necessarie per il "Giorno 1". Tutto il resto è rimandato.

    Database: Tabelle Dipendenti, Turni, Assenze (Supabase).

    Algoritmo v1:

        Rispetto Tripletta.

        Rispetto Minimi Copertura.

        No notti consecutive.

        No Mattina post Notte.

    Frontend Admin: Pagina unica con:

        Input Assenze.

        Bottone "Genera".

        Griglia modificabile.

        Pannellino laterale con "Totale Ore Previste vs Target" per ogni dipendente.

    Frontend Observer: Pagina sola lettura della griglia.

Funzionalità ESCLUSE dall'MVP (Future):

    Gestione riporto ore mesi precedenti.

    Login utenti differenziati (basta una password unica per Admin e una per Observer all'inizio).

    Statistiche avanzate annuali.

    Invio notifiche email/SMS.

6. Criteri di Accettazione (Definition of Done)

Il prodotto è pronto quando:

    L'Admin può generare un mese in meno di 180 secondi.

    Il turno generato non ha nessuna violazione "Hard" (es. 11h riposo) se matematicamente possibile.

    Tutti i dipendenti hanno un saldo ore compreso tra Target ±5h (salvo casi patologici di assenza prolungata).