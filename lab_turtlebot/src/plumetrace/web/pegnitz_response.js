// Incident response data for the Pegnitz at Nürnberg (Lederersteg reach), used by index.html.
// Researched 2026-10-14 from official Bavarian / city sources (URLs below). Phone numbers other than
// 110 / 112 come from public directories and MUST be checked before any real use. The dashboard never
// contacts anyone by itself: every escalation and every public warning is a logged recommendation or a
// drafted request to the authority that is legally allowed to act.
window.PEGNITZ_RESPONSE = {
  river: {
    name: 'Pegnitz',
    classification: 'Gewässer 1. Ordnung (state-maintained, represented by WWA Nürnberg)',
    gauge: {
      id: '24225000', name: 'Nürnberg Lederersteg / Pegnitz', operator: 'WWA Nürnberg',
      catchment_km2: 1189.6, river_km: 6.47, gauge_zero_m_nn: 288.80,
      warning_levels_cm: [260, 300, 380, 420],
      mq_m3s: 11.4, mnq_m3s: 6.76, nq_m3s: 3.48, mhq_m3s: 58.9,
      url: 'https://www.hnd.bayern.de/pegel/regnitz/nuernberg-lederersteg-24225000',
    },
    wq_station: { id: '17651', name: 'Nürnberg Lederersteg (GKD grab samples, NH4-N, DO)',
                  url: 'https://www.gkd.bayern.de' },
    // river km 6.47 at the gauge = distance to the Pegnitz mouth (confluence with the Rednitz in Fürth)
    downstream_km_to_regnitz: 6.47,
    downstream_chain: ['Pegnitz', 'Regnitz (Fürth)', 'Main (Bamberg)', 'Rhine (Mainz)'],
    bathing: 'Bathing prohibited in the Pegnitz within Nürnberg; no EU bathing waters downstream in the city. ' +
             'Norikusbucht (Wöhrder See) is UPSTREAM of this reach and not affected.',
    cso_context: 'Pegnitztalsammler storage sewer (7 chambers, ~57,500 m³) runs under the Altstadt to Klärwerk 1; ' +
                 'Nürnberg has 35 rain basins (~290,000 m³). The Pegnitz is the water body most affected by ' +
                 'combined sewer overflows. Outfalls A/B/C in this model are illustrative, not real CSO sites.',
    sources: [
      'https://www.wwa-n.bayern.de/service/notfall/index.htm',
      'https://www.nuernberg.de/internet/umweltamt/wasserhaushaltsgesetz.html',
      'https://www.nuernberg.de/internet/sun/m_pegnitztal.html',
      'https://www.gkd.bayern.de/de/fluesse/abfluss/regnitz/nuernberg-lederersteg-24225000/statistik',
      'https://www.nuernberg.de/internet/umweltamt/baden.html',
    ],
  },

  // Thresholds the dashboard classifies against (mg/L).
  thresholds: {
    nh3_n_elevated: 0.3,   // well above the GKD background median 0.04 (90th pct 0.072)
    nh3_n_alert: 0.6,      // = gateway ALERT_MG_L
    nh3_n_severe: 2.0,     // acute fish toxicity risk zone (indicative, depends on pH/temperature)
    do_low: 6.0,           // salmonid-water concern
    do_critical: 4.0,      // fish kill risk
  },

  // Escalation ladder, lowest tier first. "Escalate" moves to the next tier and logs it.
  escalation: [
    { tier: 1, name: 'Police / Fire via Integrierte Leitstelle Nürnberg', phone: '110 / 112', verified: true,
      role: 'First report. Police lead the investigation (§ 324 StGB water pollution); fire brigade for oil / ' +
            'hazardous-substance containment. They alert the city, the Gemeinde and WWA.',
      when: 'Immediately on a confirmed alert.' },
    { tier: 2, name: 'Stadt Nürnberg Umweltamt (Untere Wasserbehörde) + SUN', phone: 'via Leitstelle (no public hotline found)', verified: false,
      role: 'City water authority enforces water law locally. SUN (Stadtentwässerung und Umweltanalytik) operates ' +
            'the sewers, rain basins and CSO outfalls; can check overflow status and isolate the sewer section.',
      when: 'Source likely a sewer / CSO outfall, or pollution persists.' },
    { tier: 3, name: 'Wasserwirtschaftsamt Nürnberg (WWA)', phone: '0911 23609-0 (switchboard, verify)', verified: false,
      role: 'State technical water authority for the Pegnitz. Advises police, runs water analytics, orders fish ' +
            'examinations, writes the expert opinion (Gesamtgutachten).',
      when: 'Confirmed pollution with ecological impact, dead fish, or unknown substance.' },
    { tier: 4, name: 'Regierung von Mittelfranken (Höhere Wasserbehörde) / LfU Bayern', phone: 'via WWA', verified: false,
      role: 'Regional water authority and state environment agency (analytics, damage cases). Coordinates if ' +
            'the incident spans districts or needs state resources.',
      when: 'Large or prolonged incident, impact beyond the city.' },
    { tier: 5, name: 'IWAP Rhein warning centre (Main / Rhine)', phone: 'via LfU / StMUV', verified: false,
      role: 'International Rhine warning and alarm plan (IKSR) covers Main and tributaries: Warnung / ' +
            'Information / Suchmeldung to downstream states.',
      when: 'Pollutant load can reach the Regnitz / Main in significant amounts.' },
  ],

  // Recommended field actions shown on an alert, in order.
  actions: [
    'Hold the robot on station and repeat the sample to confirm (rule out sensor drift).',
    'Report to Police 110 / Fire 112 (Leitstelle): place, water body "Pegnitz", substance signs, time.',
    'Secure evidence (Beweissicherung): GPS position, time, photos, keep a water sample cool and dark.',
    'Check the suspected outfall for active discharge; ask SUN for CSO / rain basin overflow status.',
    'Look for dead or gasping fish, foam, colour, odour; note it in the incident log.',
    'Warn people on the banks / bridges (Lederersteg, Kettensteg, Hallertor) to avoid water contact; keep dogs out.',
    'Track the plume downstream and give the authorities an ETA to the Regnitz confluence in Fürth.',
  ],

  // Public warning: only authorities can issue (MoWaS feeds NINA, KATWARN, Cell Broadcast, radio).
  public_warning: {
    issuers: 'Integrierte Leitstelle / Katastrophenschutzbehörde Stadt Nürnberg (KATWARN, NINA via MoWaS); ' +
             'Bavarian Interior Ministry for state-wide; radio only on request of security authorities.',
    default_radius_m: 500,
    disclaimer: 'This tool cannot send a public warning. It drafts a request for the issuing authority.',
    sources: [
      'https://www.stmi.bayern.de/bevoelkerungsschutz/warndienste/',
      'https://innenministerium.bayern.de/sus/katastrophenschutz/warnungundinformation/sirenenundlautsprecher',
    ],
  },

  // Meldebogen-style fields for the incident record.
  report_fields: ['time', 'location (lat, lon)', 'water body', 'observation (colour, odour, foam, dead fish)',
                  'NH3-N mg/L', 'DO mg/L', 'suspected source', 'estimated quantity', 'reporter', 'notified tiers'],
};
