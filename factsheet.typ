// The factsheet template. Step 5 fills it: it writes everything the sheet
// prints to results/<strategy>/factsheet.json, and the charts to growth.svg
// and drawdowns.svg, then compiles this file with the JSON's path in
// sys.inputs.data. To change the look of every factsheet, change this file.

#let d = json(sys.inputs.data)

#let ink = rgb("#1d2b3a")       // the text, and the strategy
#let accent = rgb("#cfb87c")    // CU gold: the rules and the style boxes
#let quiet = luma(105)          // the small print

#set document(title: d.name)
#set page(
  paper: "us-letter",
  margin: (x: 0.6in, top: 0.6in, bottom: 0.7in),
  header: context if counter(page).get().first() > 1 {
    set text(7pt, fill: quiet)
    text(weight: "bold", d.name)
    h(1fr)
    [Hypothetical backtest]
  },
  footer: context {
    set text(6.5pt, fill: quiet)
    d.footer
    h(1fr)
    [Page #counter(page).display() of #counter(page).final().first()]
  },
)
#set text(font: ("Arial", "Helvetica"), size: 8.5pt, fill: ink, lang: "en")
#set par(leading: 0.55em)

// A section: a bold title over a gold rule, then its content.
#let section(title, body) = block(width: 100%, above: 1.3em, below: 0.4em, {
  text(9.5pt, weight: "bold", title)
  v(-0.55em)
  line(length: 100%, stroke: 1pt + accent)
  v(-0.2em)
  body
})

// A table: the first `lefts` columns are text, the rest numbers aligned
// right; rules above and below the header and at the bottom.
#let numbers(t, lefts: 1, columns: none) = {
  set text(7.5pt)
  let n = t.header.len()
  table(
    columns: if columns == none { (auto,) * lefts + (1fr,) * (n - lefts) } else { columns },
    stroke: none,
    inset: (x: 4pt, y: 2.6pt),
    align: (x, y) => if x < lefts { left } else { right },
    table.hline(stroke: 0.6pt),
    ..t.header.map(h => text(weight: "bold", h)),
    table.hline(stroke: 0.4pt),
    ..t.rows.flatten(),
    table.hline(stroke: 0.6pt),
  )
}

// A style box: the weight on each style portfolio, shaded by its size.
#let stylebox(b) = {
  let cell(v) = table.cell(fill: accent.lighten(100% - calc.min(v, 85) * 1%))[#str(v)%]
  block(breakable: false, {
    text(weight: "bold", b.title)
    set text(7pt)
    table(
      columns: (auto, 0.4in, 0.4in, 0.4in),
      rows: (auto, 0.27in, 0.27in),
      align: center + horizon,
      inset: 3pt,
      stroke: (x, y) => if x > 0 and y > 0 { 0.4pt + luma(160) } else { none },
      [], [Value], [Blend], [Growth],
      [Large], cell(b.cells.at(0)), cell(b.cells.at(1)), cell(b.cells.at(2)),
      [Small], cell(b.cells.at(3)), cell(b.cells.at(4)), cell(b.cells.at(5)),
    )
    v(-0.3em)
    [T-bills #(b.tbills)%. R² #(b.rsq)%. \ Intercept #(b.intercept)% a year.]
  })
}

// ------------------------------- Page 1 -------------------------------

#grid(
  columns: (1fr, auto),
  align: (left + bottom, right + bottom),
  {
    text(20pt, weight: "bold", d.name)
    linebreak()
    text(8.5pt, fill: quiet, d.subtitle)
  },
  box(fill: ink, inset: (x: 9pt, y: 7pt), radius: 2pt, align(center, {
    text(10pt, weight: "bold", fill: white)[HYPOTHETICAL BACKTEST]
    linebreak()
    text(6.5pt, fill: white)[Not the results of actual trading]
  })),
)

#grid(
  columns: (1.85in, 1fr),
  column-gutter: 0.28in,
  section("Strategy facts", {
    set text(7.5pt)
    table(
      columns: (auto, 1fr),
      stroke: none,
      inset: (x: 0pt, y: 3pt),
      column-gutter: 6pt,
      ..d.facts.map(f => (text(weight: "bold", f.at(0)), f.at(1))).flatten(),
    )
  }),
  {
    section("The strategy", {
      if d.objective != "" { par[*Objective.* #d.objective] }
      par(justify: true, d.description)
    })
    section("Growth of $10,000", image(d.growth, width: 100%))
    section("Drawdowns: the fall from the last peak", image(d.drawdowns, width: 100%))
    section("Returns, % a year", numbers(d.periods))
    section("Calendar-year returns, %", numbers(d.calendar))
  },
)

#pagebreak()

// ------------------------------- Page 2 -------------------------------

#grid(
  columns: (1fr, 1fr),
  column-gutter: 0.28in,
  section("Risk and return", numbers(d.risk)),
  section("Style", stack(dir: ltr, spacing: 0.2in, ..d.style.map(stylebox))),
)

#section("Alpha: return the factor models do not explain",
  numbers(d.alphas, columns: (auto, auto, auto) + (1fr,) * 6))
#v(0.5em)

#grid(
  columns: (1fr, 1fr),
  column-gutter: 0.28in,
  section("Industry weights, %", numbers(d.industries)),
  section("Largest holdings, %", {
    for h in d.holdings {
      text(weight: "bold", h.title)
      numbers((header: ("Ticker", "Company", "Weight"), rows: h.rows),
              lefts: 2, columns: (auto, 1fr, auto))
    }
  }),
)

#section("How it was made", text(7pt, d.method))
