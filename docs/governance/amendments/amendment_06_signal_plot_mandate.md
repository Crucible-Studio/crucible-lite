# Amendment 6 — Signal Plot Mandate
*Traces to: Article I + II*
*Status: PROPOSED — ratify when Stage 1 begins*

After any change to the project's signal model or any filter coefficient in firmware
source, an agent must generate a signal plot, save it to `docs/plots/`, and wait for
human visual confirmation before proceeding.

Signal plots are the primary mechanism for catching silent model errors that pass
numerical tests. Human visual review of physical plausibility cannot be substituted
by a numerical test. A metric value that looks correct can be produced by a physically
implausible signal.

**Invoked by:** `/plot-profile` and `/plot-evidence signal`
