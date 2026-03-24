Yes — using the **same cosmic-muon model** and **same scope model** as before, I can walk through the full calculation at **one voltage point: 2000 V** for all four cases.

# Fixed assumptions

I am keeping the same assumptions from the earlier muon estimate so the numbers stay consistent.

## Geometry

- Effective outer grounded cylinder radius:

$$
b = 5\ \text{mm} = 0.5\ \text{cm}
$$

## Wire 1: thin Ni-coated CF wire

- CF core diameter = $7.7\ \mu\text{m}$
- Ni coating = $0.3\ \mu\text{m}$ on each side
- Total diameter:

$$
d = 7.7 + 2(0.3) = 8.3\ \mu\text{m}
$$

- Wire radius:

$$
a = 4.15\ \mu\text{m} = 4.15\times10^{-4}\ \text{cm}
$$

## Wire 2: 25 µm carbon fiber wire

- Diameter:

$$
d = 25\ \mu\text{m}
$$

- Radius:

$$
a = 12.5\ \mu\text{m} = 1.25\times10^{-3}\ \text{cm}
$$

## Cosmic-muon ionization assumptions

These are the same working numbers I used before.

- In **75Ar25CO2**:

$$
N_0 = 130\ \text{primary electrons}
$$

Survival factor:

$$
f_{\text{surv}} = 0.95
$$

- In **air**:

$$
N_0 = 70\ \text{primary electrons}
$$

For the clean-signal estimate I take:

$$
M = 1
$$

because I am **not** treating air as a stable proportional-avalanche case.

## Scope/readout model

Same as before:

- Termination:

$$
R = 50\ \Omega
$$

- Pulse width:

$$
\tau = 10\ \text{ns} = 1.0\times10^{-8}\ \text{s}
$$

Then:

$$
V_{\text{peak}} = \frac{Q}{\tau}R
$$

with electron charge:

$$
e = 1.602\times10^{-19}\ \text{C}
$$

---

# Shared electrostatic formula

For a cylindrical proportional-counter model, the wire surface field is

$$
E_s = \frac{V}{a\ln(b/a)}
$$

We now evaluate this at

$$
V = 2000\ \text{V}
$$

---

# Case 1: 2000 V, thin Ni-coated CF wire, 75Ar25CO2

## Step 1: geometric log factor

$$
\ln(b/a) = \ln\left(\frac{0.5}{4.15\times10^{-4}}\right)
$$

$$
\frac{0.5}{4.15\times10^{-4}} = 1204.82
$$

$$
\ln(b/a) = \ln(1204.82) = 7.094
$$

## Step 2: wire surface field

$$
E_s = \frac{2000}{(4.15\times10^{-4})(7.094)}
$$

First compute the denominator:

$$
(4.15\times10^{-4})(7.094)=2.944\times10^{-3}\ \text{cm}
$$

So:

$$
E_s = \frac{2000}{2.944\times10^{-3}} = 6.793\times10^5\ \text{V/cm}
$$

$$
E_s = 679.3\ \text{kV/cm}
$$

## Step 3: gas-gain threshold parameter $V_0$

Using the same Diethorn-style surrogate as before:

$$
V_0 = p\,a\,\ln(b/a)\left(\frac{E_{\min}}{p}\right)
$$

with

$$
p = 760\ \text{Torr}, \qquad \frac{E_{\min}}{p}=50\ \text{V/(cm\cdot Torr)}
$$

So:

$$
V_0 = 760(4.15\times10^{-4})(7.094)(50)
$$

$$
V_0 = 111.9\ \text{V}
$$

## Step 4: gas gain $M$

Using

$$
\ln M =
\frac{V}{\ln(b/a)}\frac{\ln 2}{\Delta V}
\ln\left(\frac{V}{V_0}\right)
$$

with

$$
\Delta V = 35\ \text{V}
$$

Substitute:

$$
\ln M =
\frac{2000}{7.094}\cdot\frac{\ln2}{35}\cdot
\ln\left(\frac{2000}{111.9}\right)
$$

Now compute each factor:

$$
\frac{2000}{7.094}=281.93
$$

$$
\frac{\ln2}{35} = \frac{0.6931}{35}=0.01980
$$

$$
\frac{2000}{111.9}=17.87
$$

$$
\ln(17.87)=2.883
$$

So:

$$
\ln M = 281.93 \times 0.01980 \times 2.883
$$

$$
\ln M = 16.10
$$

Therefore:

$$
M = e^{16.10} = 9.82\times10^6
$$

## Step 5: total collected charge

$$
Q = N_0 f_{\text{surv}} e M
$$

$$
Q = 130 \times 0.95 \times (1.602\times10^{-19}) \times (9.82\times10^6)
$$

First:

$$
130\times0.95 = 123.5
$$

Then:

$$
123.5 \times 1.602\times10^{-19} = 1.978\times10^{-17}\ \text{C}
$$

Then:

$$
Q = (1.978\times10^{-17})(9.82\times10^6)
$$

$$
Q = 1.94\times10^{-10}\ \text{C}
$$

In pC:

$$
Q = 194\ \text{pC}
$$

## Step 6: peak scope voltage

$$
V_{\text{peak}}=\frac{Q}{\tau}R
$$

$$
V_{\text{peak}}=
\frac{1.94\times10^{-10}}{1.0\times10^{-8}}\times 50
$$

$$
V_{\text{peak}}=0.971\ \text{V}
$$

$$
V_{\text{peak}}=971\ \text{mV}
$$

## Result

At **2000 V**, for the **thin Ni-coated wire in 75Ar25CO2**:

- Surface field:

$$
679.3\ \text{kV/cm}
$$

- Gain:

$$
9.82\times10^6
$$

- Collected charge:

$$
194\ \text{pC}
$$

- Peak signal:

$$
971\ \text{mV}
$$

**Conclusion:** comfortably visible, far above threshold.

---

# Case 2: 2000 V, 25 µm carbon fiber wire, 75Ar25CO2

## Step 1: geometric log factor

$$
\ln(b/a)=\ln\left(\frac{0.5}{1.25\times10^{-3}}\right)
$$

$$
\frac{0.5}{1.25\times10^{-3}}=400
$$

$$
\ln(b/a)=\ln(400)=5.991
$$

## Step 2: wire surface field

$$
E_s=\frac{2000}{(1.25\times10^{-3})(5.991)}
$$

Denominator:

$$
(1.25\times10^{-3})(5.991)=7.489\times10^{-3}\ \text{cm}
$$

So:

$$
E_s=\frac{2000}{7.489\times10^{-3}}=2.670\times10^5\ \text{V/cm}
$$

$$
E_s=267.0\ \text{kV/cm}
$$

## Step 3: $V_0$

$$
V_0 = 760(1.25\times10^{-3})(5.991)(50)
$$

$$
V_0 = 284.6\ \text{V}
$$

## Step 4: gas gain $M$

$$
\ln M=
\frac{2000}{5.991}\cdot\frac{\ln2}{35}\cdot
\ln\left(\frac{2000}{284.6}\right)
$$

Compute factors:

$$
\frac{2000}{5.991}=333.81
$$

$$
\frac{\ln2}{35}=0.01980
$$

$$
\frac{2000}{284.6}=7.03
$$

$$
\ln(7.03)=1.950
$$

So:

$$
\ln M = 333.81\times0.01980\times1.950
$$

$$
\ln M = 12.89
$$

Thus:

$$
M=e^{12.89}=3.96\times10^5
$$

## Step 5: collected charge

$$
Q = 130 \times 0.95 \times (1.602\times10^{-19}) \times (3.96\times10^5)
$$

We already had:

$$
130\times0.95\times1.602\times10^{-19}
=1.978\times10^{-17}\ \text{C}
$$

So:

$$
Q=(1.978\times10^{-17})(3.96\times10^5)
$$

$$
Q=7.84\times10^{-12}\ \text{C}
$$

In pC:

$$
Q=7.84\ \text{pC}
$$

## Step 6: peak scope voltage

$$
V_{\text{peak}}=
\frac{7.84\times10^{-12}}{1.0\times10^{-8}}\times50
$$

$$
V_{\text{peak}}=0.0392\ \text{V}
$$

$$
V_{\text{peak}}=39.2\ \text{mV}
$$

## Result

At **2000 V**, for the **25 µm CF wire in 75Ar25CO2**:

- Surface field:

$$
267.0\ \text{kV/cm}
$$

- Gain:

$$
3.96\times10^5
$$

- Collected charge:

$$
7.84\ \text{pC}
$$

- Peak signal:

$$
39.2\ \text{mV}
$$

**Conclusion:** clearly visible and into the “reliable” region.

---

# Case 3: 2000 V, thin Ni-coated CF wire, air

Here I use the same logic as before:

- A cosmic muon gives about

$$
N_0 = 70
$$

primary electrons in the assumed path.

- For **clean signal estimation in air**, I do **not** apply stable proportional avalanche gain, so:

$$
M=1
$$

## Step 1: field at the wire

This is the same geometry as Case 1, so:

$$
E_s = 679.3\ \text{kV/cm}
$$

## Step 2: collected charge

$$
Q = N_0 e
$$

$$
Q = 70 \times 1.602\times10^{-19}
$$

$$
Q = 1.121\times10^{-17}\ \text{C}
$$

In pC:

$$
Q = 1.121\times10^{-5}\ \text{pC}
$$

## Step 3: peak scope voltage

$$
V_{\text{peak}}=
\frac{1.121\times10^{-17}}{1.0\times10^{-8}}\times50
$$

$$
V_{\text{peak}} = 5.61\times10^{-8}\ \text{V}
$$

$$
V_{\text{peak}} = 0.0561\ \mu\text{V}
$$

## Result

At **2000 V**, for the **thin Ni-coated wire in air**:

- Surface field:

$$
679.3\ \text{kV/cm}
$$

- Clean-signal charge:

$$
1.12\times10^{-17}\ \text{C}
$$

- Peak signal:

$$
0.0561\ \mu\text{V}
$$

**Conclusion:** the clean direct muon pulse is far too small for a normal scope.

### Important caveat

At this field, the wire is in the neighborhood where **air-corona / unstable behavior** may start to matter. So if you actually see large pulses in air near this voltage, they are more likely due to **corona / discharge-like processes** than a clean proportional muon pulse.

---

# Case 4: 2000 V, 25 µm carbon fiber wire, air

Again:

- Primary electrons:

$$
N_0 = 70
$$

- No stable proportional gain assumed:

$$
M=1
$$

## Step 1: field at the wire

This is the same geometry as Case 2, so:

$$
E_s = 267.0\ \text{kV/cm}
$$

## Step 2: collected charge

Exactly the same direct primary charge as Case 3:

$$
Q = 70 \times 1.602\times10^{-19} = 1.121\times10^{-17}\ \text{C}
$$

$$
Q = 1.121\times10^{-5}\ \text{pC}
$$

## Step 3: peak scope voltage

$$
V_{\text{peak}}=
\frac{1.121\times10^{-17}}{1.0\times10^{-8}}\times50=5.61\times10^{-8}\ \text{V}
$$

$$
V_{\text{peak}} = 0.0561\ \mu\text{V}
$$

## Result

At **2000 V**, for the **25 µm CF wire in air**:

- Surface field:

$$
267.0\ \text{kV/cm}
$$

- Clean-signal charge:

$$
1.12\times10^{-17}\ \text{C}
$$

- Peak signal:

$$
0.0561\ \mu\text{V}
$$

**Conclusion:** also far too small for normal scope visibility.

In this case, unlike the thin wire, **2000 V is still less suggestive of immediate air-corona onset**, so this one is even more straightforwardly “not enough” for a clean direct muon pulse.

---

# Final comparison at 2000 V

| Wire | Gas | $E_s$ (kV/cm) | Gain $M$ | Charge $Q$ | $V_{\text{peak}}$ | What that means |
|---|---:|---:|---:|---:|---:|---|
| 8.3 µm total dia. Ni-coated CF | 75Ar25CO2 | 679.3 | $9.82\times10^6$ | 194 pC | 971 mV | extremely visible |
| 25 µm CF | 75Ar25CO2 | 267.0 | $3.96\times10^5$ | 7.84 pC | 39.2 mV | clearly visible |
| 8.3 µm total dia. Ni-coated CF | air | 679.3 | 1 | $1.12\times10^{-17}$ C | 0.0561 µV | not visible as clean muon pulse |
| 25 µm CF | air | 267.0 | 1 | $1.12\times10^{-17}$ C | 0.0561 µV | not visible as clean muon pulse |

# Main takeaway

At **2000 V** for a **cosmic muon**:

- Both wires in **75Ar25CO2** should give visible signals.
- The **thin Ni-coated wire** is much stronger because its surface field is much higher, so its gain is much higher.
- In **air**, the clean direct muon signal remains tiny for both wires; if you see something large for the thin wire, it is likely because you have moved into **air-corona / unstable discharge behavior**, not because you are running a nice proportional counter.

The next most useful follow-up would be to do the same **single-point worked derivation at 1700 V and 1800 V**, since those are closer to the practical threshold region.
