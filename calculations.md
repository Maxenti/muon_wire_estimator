# Calculations

## Yes

Yes — the earlier numbers were based on a **single cosmic-muon / MIP-like event**, specifically a **single track crossing about 1 cm of gas** near the wire.

For the scope side, I was using a **50 Ω terminated Tektronix-style input** with a conservative visibility target of about **5 mV to notice** and **20 mV to see comfortably**. Tektronix datasheets do show 50 Ω inputs on many models, 1 mV/div sensitivity, and typical RMS noise at 1 mV/div in the ~0.17–0.18 mV range, so that visibility criterion is reasonable rather than optimistic. ([Tektronix][1])

## Beta-source model I’m using now

A real **Sr-90 source** in equilibrium is really an **Sr-90 / Y-90 source**:

- **Sr-90** beta: endpoint **546 keV**, average about **196 keV**
- **Y-90** beta: endpoint **2283.9 keV**, average about **939 keV**

Those are the right energies to use for a realistic lab beta source; in practice, the betas that actually escape a source window and short air gap are often biased toward the higher-energy **Y-90** branch. ([EZAG Holding][2])

For a **somewhat realistic single beta event**, I’ll use this reference case:

- one escaping **MeV-class beta**
- about **1 cm** effective gas traversal near the wire, to stay comparable to the earlier muon estimate
- representative electron mass stopping power

$$
\left(\frac{dE}{dx}\right)_m \approx 2.0\ \text{MeV cm}^2/\text{g}
$$

which is a reasonable MeV-electron value for low-Z gases and consistent with using ESTAR as the standard stopping-power framework; ESTAR quotes collision-stopping uncertainties of about **1–2% above 100 keV**. ([NIST][3])

## Step 1: gas densities

Using the ideal-gas law at about room temperature, \(T = 293\ \text{K}\), and 1 atm:

### Air

$$
\rho_{\text{air}} \approx 1.204\times 10^{-3}\ \text{g/cm}^3
$$

### 75Ar25CO2

Mean molar mass:

$$
M = 0.75(39.948)+0.25(44.01)=40.96\ \text{g/mol}
$$

So,

$$
\rho_{75/25} \approx 1.703\times 10^{-3}\ \text{g/cm}^3
$$

## Step 2: energy deposited in 1 cm of gas by one representative beta

$$
\Delta E = \left(\frac{dE}{dx}\right)_m \rho x
$$

with \(x=1\ \text{cm}\).

### Air

$$
\Delta E_{\text{air}} = 2.0 \times 1.204\times10^{-3}
= 2.409\times10^{-3}\ \text{MeV}
$$

$$
\Delta E_{\text{air}} \approx 2.41\ \text{keV}
$$

### 75Ar25CO2

$$
\Delta E_{75/25} = 2.0 \times 1.703\times10^{-3}
= 3.406\times10^{-3}\ \text{MeV}
$$

$$
\Delta E_{75/25} \approx 3.41\ \text{keV}
$$

## Step 3: primary ion pairs

For dry air, the recommended \(W_{\text{air}}\) is about **33.97 eV per ion pair**. For Ar–CO2 mixtures, published argon/CO2 mixture data give values that interpolate to about **28.15 eV** for a **75/25** mix. ([PubMed][4])

So:

### Air

$$
N_{e,\text{air}} = \frac{2408.6\ \text{eV}}{33.97\ \text{eV}}
\approx 70.9
$$

### 75Ar25CO2

$$
N_{e,75/25} = \frac{3405.8\ \text{eV}}{28.15\ \text{eV}}
\approx 121.0
$$

That is the key result:

- **single realistic beta in air:** about **71 primary electrons**
- **single realistic beta in 75Ar25CO2:** about **121 primary electrons**

So the important physics point is:

## A single Sr-90/Y-90 beta pulse is not hugely bigger than the single-muon pulse I used before

It is the **same order of magnitude**. That means the voltage thresholds shift only a little, not by many hundreds of volts.

---

# Same gain and scope model as before

## Wire geometry

### Thin Ni-coated CF wire

7.7 µm CF core + 0.3 µm Ni coating on each side

$$
d = 8.3\ \mu\text{m}, \qquad a=4.15\times10^{-4}\ \text{cm}
$$

### 25 µm carbon fiber wire

$$
d = 25\ \mu\text{m}, \qquad a=1.25\times10^{-3}\ \text{cm}
$$

Assume effective cathode radius:

$$
b = 5\ \text{mm} = 0.5\ \text{cm}
$$

Then:

### Thin wire

$$
\ln(b/a)=7.094
$$

### 25 µm wire

$$
\ln(b/a)=5.991
$$

Surface field:

$$
E_s=\frac{V}{a\ln(b/a)}
$$

Gas gain model in 75Ar25CO2:

$$
\ln M =
\frac{V}{\ln(b/a)}\frac{\ln 2}{\Delta V}
\ln\left(\frac{V}{V_0}\right)
$$

with

$$
V_0 = p\,a\,\ln(b/a)\left(\frac{E_{\min}}{p}\right)
$$

and the same working values as before:

$$
\frac{E_{\min}}{p}=50\ \text{V/(cm Torr)}, \qquad \Delta V = 35\ \text{V}
$$

This gives:

### Thin wire

$$
V_0 \approx 111.9\ \text{V}
$$

### 25 µm wire

$$
V_0 \approx 284.6\ \text{V}
$$

For the 75/25 gas, I again keep a conservative survival factor:

$$
f_{\text{surv}} = 0.95
$$

So the collected charge from one beta is

$$
Q = N_0\,f_{\text{surv}}\,e\,M
$$

with

$$
N_0 = 121.0
$$

Therefore

$$
Q = 121.0 \times 0.95 \times e \times M
$$

$$
Q \approx 1.841\times10^{-17} M\ \text{C}
$$

In pC:

$$
Q(\text{pC}) \approx 1.841\times10^{-5} M
$$

And for a 10 ns pulse into 50 Ω:

$$
V_{\text{peak}} = \frac{Q}{\tau}R
$$

which becomes

$$
V_{\text{peak}}(\text{mV}) \approx 5\,Q(\text{pC})
$$

So:

- **barely visible**: \(V_{\text{peak}} \gtrsim 5\ \text{mV}\)
- **reliable**: \(V_{\text{peak}} \gtrsim 20\ \text{mV}\)

---

## Worked example: thin wire in 75Ar25CO2 at 1700 V

### Surface field

$$
E_s = \frac{1700}{(4.15\times10^{-4})(7.094)}
= 5.774\times10^5\ \text{V/cm}
$$

$$
E_s = 577.4\ \text{kV/cm}
$$

### Gain

$$
\ln M =
\frac{1700}{7.094}\frac{\ln2}{35}\ln\left(\frac{1700}{111.9}\right)
\approx 12.91
$$

$$
M \approx 4.06\times10^5
$$

### Charge

$$
Q(\text{pC}) \approx 1.841\times10^{-5}\times 4.06\times10^5
\approx 7.47\ \text{pC}
$$

### Scope voltage

$$
V_{\text{peak}} \approx 5\times 7.47 = 37.4\ \text{mV}
$$

### Verdict

**Reliable**

---

# 1) 7.7 µm core CF + 0.3 µm Ni, in 75Ar25CO2

| V (V) | \(E_s\) (kV/cm) | Gain \(M\) | \(Q\) (pC) | \(V_{\text{peak}}\) (mV) | Verdict |
| ----: | --------------: | ---------: | ---------: | -----------------------: | ------- |
|     0 |             0.0 |   1.00e+00 |   1.84e-05 |                 9.21e-05 | not enough |
|   100 |            34.0 |   1.00e+00 |   1.84e-05 |                 9.21e-05 | not enough |
|   200 |            67.9 |   1.38e+00 |   2.55e-05 |                 1.27e-04 | not enough |
|   300 |           101.9 |   2.28e+00 |   4.21e-05 |                 2.10e-04 | not enough |
|   400 |           135.9 |   4.15e+00 |   7.64e-05 |                 3.82e-04 | not enough |
|   500 |           169.8 |   8.08e+00 |   1.49e-04 |                 7.43e-04 | not enough |
|   600 |           203.8 |   1.67e+01 |   3.07e-04 |                 1.54e-03 | not enough |
|   700 |           237.8 |   3.60e+01 |   6.62e-04 |                 3.31e-03 | not enough |
|   800 |           271.7 |   8.09e+01 |   1.49e-03 |                 7.45e-03 | not enough |
|   900 |           305.7 |   1.88e+02 |   3.46e-03 |                 1.73e-02 | not enough |
|  1000 |           339.7 |   4.53e+02 |   8.34e-03 |                 4.17e-02 | not enough |
|  1100 |           373.6 |   1.12e+03 |   2.06e-02 |                 1.03e-01 | not enough |
|  1200 |           407.6 |   2.83e+03 |   5.21e-02 |                 2.61e-01 | not enough |
|  1300 |           441.6 |   7.34e+03 |   1.35e-01 |                 6.76e-01 | not enough |
|  1400 |           475.5 |   1.95e+04 |   3.58e-01 |                     1.79 | not enough |
|  1500 |           509.5 |   5.26e+04 |   9.68e-01 |                     4.84 | not enough / right on edge |
|  1600 |           543.5 |   1.45e+05 |       2.67 |                     13.3 | barely visible |
|  1700 |           577.4 |   4.06e+05 |       7.47 |                     37.4 | reliable |
|  1800 |           611.4 |   1.16e+06 |       21.3 |                      106 | reliable |
|  1900 |           645.4 |   3.34e+06 |       61.6 |                      308 | reliable |
|  2000 |           679.3 |   9.82e+06 |        181 |                      904 | reliable |

## Result

- **first likely visible:** about **1600 V**
- **good no-luck voltage:** about **1700 V**

This is only about **100 V tougher** than the earlier muon-style estimate, because the primary ionization count stayed very similar.

---

# 2) 25 µm carbon fiber, in 75Ar25CO2

| V (V) | \(E_s\) (kV/cm) | Gain \(M\) | \(Q\) (pC) | \(V_{\text{peak}}\) (mV) | Verdict |
| ----: | --------------: | ---------: | ---------: | -----------------------: | ------- |
|     0 |             0.0 |   1.00e+00 |   1.84e-05 |                 9.21e-05 | not enough |
|   100 |            13.4 |   1.00e+00 |   1.84e-05 |                 9.21e-05 | not enough |
|   200 |            26.7 |   1.00e+00 |   1.84e-05 |                 9.21e-05 | not enough |
|   300 |            40.1 |   1.05e+00 |   1.93e-05 |                 9.66e-05 | not enough |
|   400 |            53.4 |   1.57e+00 |   2.89e-05 |                 1.45e-04 | not enough |
|   500 |            66.8 |   2.54e+00 |   4.67e-05 |                 2.34e-04 | not enough |
|   600 |            80.1 |   4.39e+00 |   8.08e-05 |                 4.04e-04 | not enough |
|   700 |            93.5 |   8.02e+00 |   1.48e-04 |                 7.38e-04 | not enough |
|   800 |           106.8 |   1.54e+01 |   2.84e-04 |                 1.42e-03 | not enough |
|   900 |           120.2 |   3.07e+01 |   5.65e-04 |                 2.82e-03 | not enough |
|  1000 |           133.5 |   6.37e+01 |   1.17e-03 |                 5.87e-03 | not enough |
|  1100 |           146.9 |   1.36e+02 |   2.50e-03 |                 1.25e-02 | not enough |
|  1200 |           160.2 |   3.01e+02 |   5.55e-03 |                 2.77e-02 | not enough |
|  1300 |           173.6 |   6.84e+02 |   1.26e-02 |                 6.29e-02 | not enough |
|  1400 |           186.9 |   1.59e+03 |   2.93e-02 |                 1.47e-01 | not enough |
|  1500 |           200.3 |   3.79e+03 |   6.99e-02 |                 3.49e-01 | not enough |
|  1600 |           213.6 |   9.25e+03 |   1.70e-01 |                 8.51e-01 | not enough |
|  1700 |           227.0 |   2.30e+04 |   4.24e-01 |                     2.12 | not enough |
|  1800 |           240.3 |   5.83e+04 |       1.07 |                     5.37 | barely visible |
|  1900 |           253.7 |   1.51e+05 |       2.78 |                     13.9 | barely visible |
|  2000 |           267.0 |   3.96e+05 |       7.30 |                     36.5 | reliable |
|  2100 |           280.4 |   1.06e+06 |       19.5 |                     97.5 | reliable |
|  2200 |           293.8 |   2.88e+06 |       53.0 |                      265 | reliable |

## Result

- **first likely visible:** about **1800 V**
- **good no-luck voltage:** about **2000 V**

So this one is basically unchanged from the muon-style estimate.

---

# 3) 7.7 µm core CF + 0.3 µm Ni, in air

For air, I do **not** treat this as a clean proportional-avalanche counter. The direct primary pulse from one realistic beta is just:

$$
Q_{\text{air}} = 70.9\,e
\approx 1.136\times10^{-17}\ \text{C}
$$

$$
Q_{\text{air}} \approx 1.136\times10^{-5}\ \text{pC}
$$

So into 50 Ω with a 10 ns pulse,

$$
V_{\text{peak}} \approx 0.0568\ \mu\text{V}
$$

That is still far too small.

Using the same rough corona-onset estimate as before, the thin wire enters the dangerous air-corona neighborhood at roughly **1.4 kV**, but that is not a clean proportional single-beta signal.

| V (V) | \(E_s\) (kV/cm) | \(Q\) (pC), no avalanche | \(V_{\text{peak}}\) (µV) | Verdict | Interpretation |
| ----: | --------------: | -----------------------: | -----------------------: | ------- | -------------- |
|     0 |             0.0 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   100 |            34.0 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   200 |            67.9 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   300 |           101.9 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   400 |           135.9 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   500 |           169.8 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   600 |           203.8 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   700 |           237.8 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   800 |           271.7 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   900 |           305.7 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1000 |           339.7 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1100 |           373.6 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1200 |           407.6 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1300 |           441.6 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1400 |           475.5 |                1.136e-05 |                   0.0568 | unstable corona region | may show discharge-like activity, not clean beta pulses |
|  1500 |           509.5 |                1.136e-05 |                   0.0568 | unstable corona region | may show discharge-like activity, not clean beta pulses |
|  1600 |           543.5 |                1.136e-05 |                   0.0568 | unstable corona region | may show discharge-like activity, not clean beta pulses |
|  1700 |           577.4 |                1.136e-05 |                   0.0568 | unstable corona region | may show discharge-like activity, not clean beta pulses |

## Result

- **clean single-beta pulse on a scope in air:** **no**
- **below ~1400 V:** definitely no
- **above ~1400 V:** you may enter air-corona behavior, but that is **not** a clean single-beta detection mode

---

# 4) 25 µm carbon fiber, in air

Same direct primary pulse as above:

$$
Q_{\text{air}} \approx 1.136\times10^{-5}\ \text{pC}
$$

$$
V_{\text{peak}} \approx 0.0568\ \mu\text{V}
$$

Again, far too small.

With the same rough air-corona estimate, the 25 µm wire does not get near that region until roughly **2.1–2.2 kV**.

| V (V) | \(E_s\) (kV/cm) | \(Q\) (pC), no avalanche | \(V_{\text{peak}}\) (µV) | Verdict | Interpretation |
| ----: | --------------: | -----------------------: | -----------------------: | ------- | -------------- |
|     0 |             0.0 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   100 |            13.4 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   200 |            26.7 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   300 |            40.1 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   400 |            53.4 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   500 |            66.8 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   600 |            80.1 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   700 |            93.5 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   800 |           106.8 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|   900 |           120.2 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1000 |           133.5 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1100 |           146.9 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1200 |           160.2 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1300 |           173.6 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1400 |           186.9 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1500 |           200.3 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1600 |           213.6 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1700 |           227.0 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1800 |           240.3 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  1900 |           253.7 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  2000 |           267.0 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  2100 |           280.4 |                1.136e-05 |                   0.0568 | not enough | below corona region |
|  2200 |           293.8 |                1.136e-05 |                   0.0568 | unstable corona region | may show discharge-like activity, not clean beta pulses |

## Result

- **clean single-beta pulse on a scope in air:** **no**
- **below ~2200 V:** no
- **above ~2200 V:** you are getting into unstable air behavior, not a clean proportional signal

---

# Final answer

For a **somewhat realistic single Sr-90/Y-90 beta event**, the answer is:

| Wire | Gas | First likely visible | Comfortable / reliable |
| ---- | ---:| -------------------: | ---------------------: |
| **7.7 µm core CF + 0.3 µm Ni** | **75Ar25CO2** | **1600 V** | **1700 V** |
| **25 µm carbon fiber** | **75Ar25CO2** | **1800 V** | **2000 V** |
| **7.7 µm core CF + 0.3 µm Ni** | **Air** | **no clean proportional beta pulse** | **only unstable corona region ~1400 V+** |
| **25 µm carbon fiber** | **Air** | **no clean proportional beta pulse** | **only unstable corona region ~2200 V+** |

## Most important physical takeaway

A **single realistic Sr-90/Y-90 beta** does **not** give you an enormously larger pulse than the **single cosmic-muon** estimate from before. For a ~1 cm gas path, the number of primary ion pairs stays around **tens to a bit over one hundred**, so the scope-visibility voltages stay in essentially the **same range**.

If you want the next step, the most useful improvement would be a **source-geometry-aware beta calculation**: source window thickness, source-to-wire distance, air gap, collimation, and actual beta angle/track-length distribution. That can shift the threshold more meaningfully than swapping “muon” to “beta” in the simple 1 cm single-track model.

[1]: https://www.tek.com/en/datasheet/mixed-signal-oscilloscopes?utm_source=chatgpt.com "Mixed Signal Oscilloscopes"
[2]: https://www.ezag.com/fileadmin/ezag/user-uploads/isotopes/isotopes/Isotrak/isotrak-pdf/Decay_Schema_Data/Sr-90_Y-90.pdf?utm_source=chatgpt.com "Recommended Nuclear Decay Data"
[3]: https://physics.nist.gov/PhysRefData/Star/Text/ESTAR.html?utm_source=chatgpt.com "ESTAR"
[4]: https://pubmed.ncbi.nlm.nih.gov/31424563/?utm_source=chatgpt.com "Determination of Wair in high-energy electron beams using ..."
