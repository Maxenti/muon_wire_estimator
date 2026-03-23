I’ve got the scope side narrowed to a concrete visibility target next; after that I’m building the voltage-by-voltage estimates for both wires and both gases using one consistent cylindrical-wire model so the tables are comparable.

Thought for 6m 54s
Bottom line

Using a conservative direct-to-scope, 50 Ω terminated readout model, the voltages where a standard Tektronix-class oscilloscope should start to see the pulse without needing luck come out to about:

Wire	Gas	First likely visible	Comfortable / reliable
7.7 µm CF core + 0.3 µm Ni coating (8.3 µm total dia.)	75Ar25CO2	1500 V	1700 V
25 µm carbon fiber	75Ar25CO2	1800 V	2000 V
7.7 µm CF core + 0.3 µm Ni coating	Air	No clean proportional single-muon pulse expected	Only unstable corona/discharge region ~1400 V and up
25 µm carbon fiber	Air	No clean proportional single-muon pulse expected	Only unstable corona/discharge region ~2200 V and up

That conclusion is based on a scope criterion of:

barely visible: about 5 mV
reliably visible: about 20 mV

That is a reasonable conservative criterion because Tektronix scopes commonly reach 1 mV/div, higher-end MSO/DPO families offer 50 Ω input, and Tektronix quotes typical random noise at 1 mV/div, 50 Ω in the 0.17–0.18 mV RMS range. TBS2000B-class scopes are 1 MΩ input and use external matching if you want 50 Ω behavior.

What I am assuming

Because the exact answer depends a lot on geometry and readout, I have to lock a concrete model:

Detector / geometry assumptions
single anode wire inside an effective grounded cylindrical cathode
effective cathode radius: 5 mm
gas at about 1 atm
one MIP-like muon crossing about 1 cm of gas
Wire sizes
Ni-coated thin wire
7.7 µm CF core + 0.3 µm Ni coating on each side
total diameter = 8.3 µm
radius = 4.15 µm = 4.15×10⁻⁴ cm
25 µm CF wire
radius = 12.5 µm = 1.25×10⁻³ cm
Signal/readout assumptions
direct scope readout into 50 Ω
effective fast pulse width: 10 ns
visible threshold: 5 mV
comfortable threshold: 20 mV
Gas-model assumptions for the estimate

For 75Ar25CO2, I use a simple proportional-counter/Diethorn-style avalanche surrogate:

Es=Valn⁡(b/a)
E
s
	​

=
aln(b/a)
V
	​

ln⁡M=Vln⁡(b/a)ln⁡2ΔVln⁡ ⁣(VV0),V0=p a ln⁡(b/a) (Emin⁡p)
lnM=
ln(b/a)
V
	​

ΔV
ln2
	​

ln(
V
0
	​

V
	​

),V
0
	​

=paln(b/a)(
p
E
min
	​

	​

)

with conservative working values:

Emin⁡/p=50 V/(cm Torr)
E
min
	​

/p=50 V/(cm Torr)
ΔV=35 V
ΔV=35 V

For air, I do not use that proportional-gain model, because air is strongly attaching. Below corona onset, the direct primary pulse is tiny; above onset, what you begin to see is better described as corona/discharge behavior, not a clean proportional single-muon pulse. For the onset estimate I use Peek’s law as a rough air-corona criterion.

Shared geometric numbers

With 
b=5 mm=0.5 cm
b=5 mm=0.5 cm:

Thin Ni-coated CF wire
a=4.15×10−4 cm
a=4.15×10
−4
 cm
ln⁡(b/a)=ln⁡(0.5/4.15×10−4)=7.09
ln(b/a)=ln(0.5/4.15×10
−4
)=7.09

So

Es(kV/cm)≈V4.15×10−4×7.09×10−3≈0.3397 VkV
E
s
	​

(kV/cm)≈
4.15×10
−4
×7.09
V
	​

×10
−3
≈0.3397V
kV
	​


or numerically:

1000 V → 339.7 kV/cm
1500 V → 509.5 kV/cm
1700 V → 577.4 kV/cm
25 µm CF wire
a=1.25×10−3 cm
a=1.25×10
−3
 cm
ln⁡(b/a)=ln⁡(0.5/1.25×10−3)=5.99
ln(b/a)=ln(0.5/1.25×10
−3
)=5.99

So

Es(kV/cm)≈V1.25×10−3×5.99×10−3≈0.1335 VkV
E
s
	​

(kV/cm)≈
1.25×10
−3
×5.99
V
	​

×10
−3
≈0.1335V
kV
	​


or:

1000 V → 133.5 kV/cm
1800 V → 240.3 kV/cm
2000 V → 267.0 kV/cm
How I convert charge into scope voltage

For the 75Ar25CO2 cases I take:

primary electrons per event: 130
survival factor: 0.95

So collected charge is

Q=N0 fsurv e M
Q=N
0
	​

f
surv
	​

eM
Q=130×0.95×(1.602×10−19)×M
Q=130×0.95×(1.602×10
−19
)×M
Q≈1.978×10−17M C
Q≈1.978×10
−17
M C

Then for a 10 ns pulse into 50 Ω,

Vpeak=QτR
V
peak
	​

=
τ
Q
	​

R
Vpeak=Q10 ns×50 Ω
V
peak
	​

=
10 ns
Q
	​

×50 Ω

So:

5 mV visible requires about

Q≈1.0×10−12 C=1.0 pC
Q≈1.0×10
−12
 C=1.0 pC

20 mV reliable requires about

Q≈4.0×10−12 C=4.0 pC
Q≈4.0×10
−12
 C=4.0 pC

That is the real threshold to keep in mind.

Worked example: thin Ni-coated CF wire in 75Ar25CO2 at 1700 V
Step 1: surface field
Es=1700(4.15×10−4)(7.09)=5.774×105 V/cm
E
s
	​

=
(4.15×10
−4
)(7.09)
1700
	​

=5.774×10
5
 V/cm
Es=577.4 kV/cm
E
s
	​

=577.4 kV/cm
Step 2: avalanche threshold parameter
V0=760×(4.15×10−4)×7.09×50=111.9 V
V
0
	​

=760×(4.15×10
−4
)×7.09×50=111.9 V
Step 3: gas gain
ln⁡M=17007.09ln⁡235ln⁡(1700111.9)
lnM=
7.09
1700
	​

35
ln2
	​

ln(
111.9
1700
	​

)
17007.09=239.8,ln⁡235=0.01980,ln⁡(15.19)=2.720
7.09
1700
	​

=239.8,
35
ln2
	​

=0.01980,ln(15.19)=2.720
ln⁡M≈12.91
lnM≈12.91
M≈e12.91≈4.06×105
M≈e
12.91
≈4.06×10
5
Step 4: collected charge
Q=130×0.95×(1.602×10−19)×4.06×105
Q=130×0.95×(1.602×10
−19
)×4.06×10
5
Q≈8.03×10−12 C=8.03 pC
Q≈8.03×10
−12
 C=8.03 pC
Step 5: scope voltage
Vpeak=8.03×10−1210×10−9×50
V
peak
	​

=
10×10
−9
8.03×10
−12
	​

×50
Vpeak≈4.01×10−2 V=40.1 mV
V
peak
	​

≈4.01×10
−2
 V=40.1 mV
Verdict

40.1 mV is well above the 20 mV reliable threshold.
So 1700 V is a good “should see it without luck” voltage for the thin wire in 75Ar25CO2.

Case 1: 7.7 µm CF core + 0.3 µm Ni coating, in 75Ar25CO2
V (V)	E_s (kV/cm)	Gain M	Q (pC)	V_peak (mV)	Scope?
0	0.0	1.00e+00	1.98e-05	9.89e-05	not enough
100	34.0	1.00e+00	1.98e-05	9.89e-05	not enough
200	67.9	1.38e+00	2.74e-05	0.000137	not enough
300	101.9	2.28e+00	4.52e-05	0.000226	not enough
400	135.9	4.15e+00	8.21e-05	0.000410	not enough
500	169.8	8.08e+00	1.60e-04	0.000800	not enough
600	203.8	1.67e+01	3.30e-04	0.00165	not enough
700	237.8	3.60e+01	7.12e-04	0.00356	not enough
800	271.7	8.09e+01	1.60e-03	0.00801	not enough
900	305.7	1.88e+02	3.73e-03	0.0186	not enough
1000	339.7	4.53e+02	8.95e-03	0.0448	not enough
1100	373.6	1.12e+03	2.21e-02	0.111	not enough
1200	407.6	2.83e+03	5.60e-02	0.280	not enough
1300	441.6	7.34e+03	1.45e-01	0.726	not enough
1400	475.5	1.95e+04	3.85e-01	1.92	not enough
1500	509.5	5.26e+04	1.04	5.20	barely visible
1600	543.5	1.45e+05	2.86	14.3	barely visible
1700	577.4	4.06e+05	8.03	40.1	reliable
1800	611.4	1.16e+06	22.9	114	reliable
1900	645.4	3.34e+06	66.2	331	reliable
2000	679.3	9.82e+06	194	971	reliable
Result for this case
first likely visible: 1500 V
good no-luck operating point: 1700 V
Case 2: 25 µm carbon fiber, in 75Ar25CO2
V (V)	E_s (kV/cm)	Gain M	Q (pC)	V_peak (mV)	Scope?
0	0.0	1.00e+00	1.98e-05	9.89e-05	not enough
100	13.4	1.00e+00	1.98e-05	9.89e-05	not enough
200	26.7	1.00e+00	1.98e-05	9.89e-05	not enough
300	40.1	1.05e+00	2.08e-05	0.000104	not enough
400	53.4	1.57e+00	3.10e-05	0.000155	not enough
500	66.8	2.54e+00	5.02e-05	0.000251	not enough
600	80.1	4.39e+00	8.69e-05	0.000434	not enough
700	93.5	8.02e+00	1.59e-04	0.000794	not enough
800	106.8	1.54e+01	3.04e-04	0.00152	not enough
900	120.2	3.07e+01	6.08e-04	0.00304	not enough
1000	133.5	6.37e+01	1.26e-03	0.00630	not enough
1100	146.9	1.36e+02	2.70e-03	0.0135	not enough
1200	160.2	3.01e+02	5.96e-03	0.0298	not enough
1300	173.6	6.84e+02	1.35e-02	0.0676	not enough
1400	186.9	1.59e+03	3.15e-02	0.157	not enough
1500	200.3	3.79e+03	7.51e-02	0.375	not enough
1600	213.6	9.25e+03	1.83e-01	0.915	not enough
1700	227.0	2.30e+04	4.55e-01	2.28	not enough
1800	240.3	5.83e+04	1.15	5.77	barely visible
1900	253.7	1.51e+05	2.98	14.9	barely visible
2000	267.0	3.96e+05	7.84	39.2	reliable
2100	280.4	1.06e+06	21.0	105	reliable
2200	293.8	2.88e+06	56.9	285	reliable
2300	307.1	7.93e+06	157	784	reliable
2400	320.5	2.22e+07	439	2190	reliable
Result for this case
first likely visible: 1800 V
good no-luck operating point: 2000 V

Above roughly 2.1–2.3 kV, this simple proportional model is probably becoming too optimistic because real devices start moving toward saturation / streamer / breakdown behavior. So I would treat 2000 V as the useful engineering answer here, not the multi-volt rows.

Case 3: 7.7 µm CF core + 0.3 µm Ni coating, in air

Below corona onset, I assume essentially no useful avalanche multiplication for clean fast electron pulses in air.

The primary charge from one event is only

Qprimary=70e=70(1.602×10−19)=1.12×10−17 C
Q
primary
	​

=70e=70(1.602×10
−19
)=1.12×10
−17
 C

That gives

Vpeak=1.12×10−1710 ns×50=5.61×10−8 V=0.056 μV
V
peak
	​

=
10 ns
1.12×10
−17
	​

×50=5.61×10
−8
 V=0.056 μV

That is nowhere near visible.

Using Peek’s law as a rough air-corona criterion gives onset around:

Vcorona≈1.39 kV
V
corona
	​

≈1.39 kV

for the thin wire.

V (V)	E_s (kV/cm)	Primary Q only (pC)	Direct V_peak (µV)	Scope?	Interpretation
0	0.0	1.12e-05	0.0561	not enough	below corona onset
100	34.0	1.12e-05	0.0561	not enough	below corona onset
200	67.9	1.12e-05	0.0561	not enough	below corona onset
300	101.9	1.12e-05	0.0561	not enough	below corona onset
400	135.9	1.12e-05	0.0561	not enough	below corona onset
500	169.8	1.12e-05	0.0561	not enough	below corona onset
600	203.8	1.12e-05	0.0561	not enough	below corona onset
700	237.8	1.12e-05	0.0561	not enough	below corona onset
800	271.7	1.12e-05	0.0561	not enough	below corona onset
900	305.7	1.12e-05	0.0561	not enough	below corona onset
1000	339.7	1.12e-05	0.0561	not enough	below corona onset
1100	373.6	1.12e-05	0.0561	not enough	below corona onset
1200	407.6	1.12e-05	0.0561	not enough	below corona onset
1300	441.6	1.12e-05	0.0561	not enough	below corona onset
1400	475.5	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
1500	509.5	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
1600	543.5	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
1700	577.4	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
Result for this case
clean proportional single-muon pulse: no
below ~1400 V: definitely not enough
around 1400–1700 V: you may start to see air-corona/discharge activity, but that is not the same as a stable clean muon signal
Case 4: 25 µm carbon fiber, in air

Same direct primary pulse estimate:

Qprimary=70e=1.12×10−17 C
Q
primary
	​

=70e=1.12×10
−17
 C
Vpeak=0.056 μV
V
peak
	​

=0.056 μV

Again: nowhere near visible below avalanche/corona onset.

For the 25 µm wire, Peek-law rough onset is:

Vcorona≈2.14 kV
V
corona
	​

≈2.14 kV

V (V)	E_s (kV/cm)	Primary Q only (pC)	Direct V_peak (µV)	Scope?	Interpretation
0	0.0	1.12e-05	0.0561	not enough	below corona onset
100	13.4	1.12e-05	0.0561	not enough	below corona onset
200	26.7	1.12e-05	0.0561	not enough	below corona onset
300	40.1	1.12e-05	0.0561	not enough	below corona onset
400	53.4	1.12e-05	0.0561	not enough	below corona onset
500	66.8	1.12e-05	0.0561	not enough	below corona onset
600	80.1	1.12e-05	0.0561	not enough	below corona onset
700	93.5	1.12e-05	0.0561	not enough	below corona onset
800	106.8	1.12e-05	0.0561	not enough	below corona onset
900	120.2	1.12e-05	0.0561	not enough	below corona onset
1000	133.5	1.12e-05	0.0561	not enough	below corona onset
1100	146.9	1.12e-05	0.0561	not enough	below corona onset
1200	160.2	1.12e-05	0.0561	not enough	below corona onset
1300	173.6	1.12e-05	0.0561	not enough	below corona onset
1400	186.9	1.12e-05	0.0561	not enough	below corona onset
1500	200.3	1.12e-05	0.0561	not enough	below corona onset
1600	213.6	1.12e-05	0.0561	not enough	below corona onset
1700	227.0	1.12e-05	0.0561	not enough	below corona onset
1800	240.3	1.12e-05	0.0561	not enough	below corona onset
1900	253.7	1.12e-05	0.0561	not enough	below corona onset
2000	267.0	1.12e-05	0.0561	not enough	below corona onset
2100	280.4	1.12e-05	0.0561	not enough	below corona onset
2200	293.8	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
2300	307.1	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
2400	320.5	1.12e-05	0.0561	unstable corona region	may show discharge pulses, not clean muon pulses
Result for this case
clean proportional single-muon pulse: no
below ~2200 V: not enough
around 2200–2400 V: possible discharge/corona activity, but again not a clean stable muon signal
Final conclusions
In 75Ar25CO2

The thin Ni-coated CF wire wins clearly.

8.3 µm total dia. Ni-coated CF
starts to be visible around 1500 V
becomes comfortably visible around 1700 V
25 µm CF
starts to be visible around 1800 V
becomes comfortably visible around 2000 V
In air

For clean single-muon detection on a bare scope, the answer is basically no for both wires.

the direct primary pulse is only about 0.056 µV
that is orders of magnitude too small
what appears near the threshold voltages in air is better thought of as corona/discharge behavior, not a stable proportional muon signal

So for air:

thin Ni-coated wire: not a good clean-signal operating medium
25 µm CF wire: also not a good clean-signal operating medium
if you “see something,” it is likely because you have entered an unstable air-corona regime

If you want, I can next do the same calculation in a second pass for a 1 MΩ / capacitive Tek-scope input model, which will give a more optimistic set of voltages and is often closer to what people mean by “just put it on a scope and see if there’s a pulse.”

are all those from a cosmic muon based signal? And if so can you do all calculations again for a somewhat realistic beta source signal (Sr90)

Yes — the previous numbers were for a cosmic-muon / MIP-like event model. I’m now redoing the chain for a single Sr-90 beta event with an explicit electron energy-deposition assumption, so the new thresholds will be grounded in a beta rather than a muon.

Thought for 5m 23s
Yes

Yes — the earlier numbers were based on a single cosmic-muon / MIP-like event, specifically a single track crossing about 1 cm of gas near the wire. For the scope side, I was using a 50 Ω terminated Tektronix-style input with a conservative visibility target of about 5 mV to notice and 20 mV to see comfortably. Tektronix datasheets do show 50 Ω inputs on many models, 1 mV/div sensitivity, and typical RMS noise at 1 mV/div in the ~0.17–0.18 mV range, so that visibility criterion is reasonable rather than optimistic.

Beta-source model I’m using now

A real Sr-90 source in equilibrium is really an Sr-90 / Y-90 source:

Sr-90 beta: endpoint 546 keV, average about 196 keV
Y-90 beta: endpoint 2283.9 keV, average about 939 keV

Those are the right energies to use for a realistic lab beta source; in practice, the betas that actually escape a source window and short air gap are often biased toward the higher-energy Y-90 branch.

For a somewhat realistic single beta event, I’ll use this reference case:

one escaping MeV-class beta
about 1 cm effective gas traversal near the wire, to stay comparable to the earlier muon estimate

representative electron mass stopping power

(dEdx)m≈2.0 MeV cm2/g
(
dx
dE
	​

)
m
	​

≈2.0 MeV cm
2
/g

which is a reasonable MeV-electron value for low-Z gases and consistent with using ESTAR as the standard stopping-power framework; ESTAR quotes collision-stopping uncertainties of about 1–2% above 100 keV.

Step 1: gas densities

Using the ideal-gas law at about room temperature, 
T=293 K
T=293 K, 1 atm:

Air
ρair≈1.204×10−3 g/cm3
ρ
air
	​

≈1.204×10
−3
 g/cm
3
75Ar25CO2

Mean molar mass:

M=0.75(39.948)+0.25(44.01)=40.96 g/mol
M=0.75(39.948)+0.25(44.01)=40.96 g/mol

So

ρ75/25≈1.703×10−3 g/cm3
ρ
75/25
	​

≈1.703×10
−3
 g/cm
3
Step 2: energy deposited in 1 cm of gas by one representative beta
ΔE=(dEdx)mρx
ΔE=(
dx
dE
	​

)
m
	​

ρx

with 
x=1 cm
x=1 cm.

Air
ΔEair=2.0×1.204×10−3=2.409×10−3 MeV
ΔE
air
	​

=2.0×1.204×10
−3
=2.409×10
−3
 MeV
ΔEair≈2.41 keV
ΔE
air
	​

≈2.41 keV
75Ar25CO2
ΔE75/25=2.0×1.703×10−3=3.406×10−3 MeV
ΔE
75/25
	​

=2.0×1.703×10
−3
=3.406×10
−3
 MeV
ΔE75/25≈3.41 keV
ΔE
75/25
	​

≈3.41 keV
Step 3: primary ion pairs

For dry air, the recommended 
Wair
W
air
	​

 is about 33.97 eV per ion pair. For Ar–CO2 mixtures, published argon/CO2 mixture data give values that interpolate to about 28.15 eV for a 75/25 mix.

So:

Air
Ne,air=2408.6 eV33.97 eV≈70.9
N
e,air
	​

=
33.97 eV
2408.6 eV
	​

≈70.9
75Ar25CO2
Ne,75/25=3405.8 eV28.15 eV≈121.0
N
e,75/25
	​

=
28.15 eV
3405.8 eV
	​

≈121.0

That is the key result:

single realistic beta in air: about 71 primary electrons
single realistic beta in 75Ar25CO2: about 121 primary electrons

So the important physics point is:

A single Sr-90/Y-90 beta pulse is not hugely bigger than the single-muon pulse I used before

It is the same order of magnitude. That means the voltage thresholds shift only a little, not by many hundreds of volts.

Same gain and scope model as before
Wire geometry
Thin Ni-coated CF wire

7.7 µm CF core + 0.3 µm Ni coating on each side

d=8.3 μm,a=4.15×10−4 cm
d=8.3 μm,a=4.15×10
−4
 cm
25 µm carbon fiber wire
d=25 μm,a=1.25×10−3 cm
d=25 μm,a=1.25×10
−3
 cm

Assume effective cathode radius:

b=5 mm=0.5 cm
b=5 mm=0.5 cm

Then

Thin wire
ln⁡(b/a)=7.094
ln(b/a)=7.094
25 µm wire
ln⁡(b/a)=5.991
ln(b/a)=5.991

Surface field:

Es=Valn⁡(b/a)
E
s
	​

=
aln(b/a)
V
	​


Gas gain model in 75Ar25CO2:

ln⁡M=Vln⁡(b/a)ln⁡2ΔVln⁡ ⁣(VV0)
lnM=
ln(b/a)
V
	​

ΔV
ln2
	​

ln(
V
0
	​

V
	​

)

with

V0=p a ln⁡(b/a)(Emin⁡p)
V
0
	​

=paln(b/a)(
p
E
min
	​

	​

)

and the same working values as before:

Emin⁡p=50 V/(cm Torr),ΔV=35 V
p
E
min
	​

	​

=50 V/(cm Torr),ΔV=35 V

This gives:

Thin wire
V0≈111.9 V
V
0
	​

≈111.9 V
25 µm wire
V0≈284.6 V
V
0
	​

≈284.6 V

For the 75/25 gas, I again keep a conservative survival factor:

fsurv=0.95
f
surv
	​

=0.95

So the collected charge from one beta is

Q=N0 fsurv e M
Q=N
0
	​

f
surv
	​

eM

with

N0=121.0
N
0
	​

=121.0

Therefore

Q=121.0×0.95×e×M
Q=121.0×0.95×e×M
Q≈1.841×10−17M C
Q≈1.841×10
−17
M C

In pC:

Q(pC)≈1.841×10−5M
Q(pC)≈1.841×10
−5
M

And for a 10 ns pulse into 50 Ω:

Vpeak=QτR
V
peak
	​

=
τ
Q
	​

R

which becomes

Vpeak(mV)≈5 Q(pC)
V
peak
	​

(mV)≈5Q(pC)

So:

barely visible: 
Vpeak≳5 mV
V
peak
	​

≳5 mV
reliable: 
Vpeak≳20 mV
V
peak
	​

≳20 mV
Worked example: thin wire in 75Ar25CO2 at 1700 V
Surface field
Es=1700(4.15×10−4)(7.094)=5.774×105 V/cm
E
s
	​

=
(4.15×10
−4
)(7.094)
1700
	​

=5.774×10
5
 V/cm
Es=577.4 kV/cm
E
s
	​

=577.4 kV/cm
Gain
ln⁡M=17007.094ln⁡235ln⁡(1700111.9)≈12.91
lnM=
7.094
1700
	​

35
ln2
	​

ln(
111.9
1700
	​

)≈12.91
M≈4.06×105
M≈4.06×10
5
Charge
Q(pC)≈1.841×10−5×4.06×105≈7.47 pC
Q(pC)≈1.841×10
−5
×4.06×10
5
≈7.47 pC
Scope voltage
Vpeak≈5×7.47=37.4 mV
V
peak
	​

≈5×7.47=37.4 mV
Verdict

Reliable

1) 7.7 µm core CF + 0.3 µm Ni, in 75Ar25CO2
V (V)	
Es
E
s
	​

 (kV/cm)	Gain 
M
M	
Q
Q (pC)	
Vpeak
V
peak
	​

 (mV)	Verdict
0	0.0	1.00e+00	1.84e-05	9.21e-05	not enough
100	34.0	1.00e+00	1.84e-05	9.21e-05	not enough
200	67.9	1.38e+00	2.55e-05	1.27e-04	not enough
300	101.9	2.28e+00	4.21e-05	2.10e-04	not enough
400	135.9	4.15e+00	7.64e-05	3.82e-04	not enough
500	169.8	8.08e+00	1.49e-04	7.43e-04	not enough
600	203.8	1.67e+01	3.07e-04	1.54e-03	not enough
700	237.8	3.60e+01	6.62e-04	3.31e-03	not enough
800	271.7	8.09e+01	1.49e-03	7.45e-03	not enough
900	305.7	1.88e+02	3.46e-03	1.73e-02	not enough
1000	339.7	4.53e+02	8.34e-03	4.17e-02	not enough
1100	373.6	1.12e+03	2.06e-02	1.03e-01	not enough
1200	407.6	2.83e+03	5.21e-02	2.61e-01	not enough
1300	441.6	7.34e+03	1.35e-01	6.76e-01	not enough
1400	475.5	1.95e+04	3.58e-01	1.79	not enough
1500	509.5	5.26e+04	9.68e-01	4.84	not enough / right on edge
1600	543.5	1.45e+05	2.67	13.3	barely visible
1700	577.4	4.06e+05	7.47	37.4	reliable
1800	611.4	1.16e+06	21.3	106	reliable
1900	645.4	3.34e+06	61.6	308	reliable
2000	679.3	9.82e+06	181	904	reliable
Result
first likely visible: about 1600 V
good no-luck voltage: about 1700 V

This is only about 100 V tougher than the earlier muon-style estimate, because the primary ionization count stayed very similar.

2) 25 µm carbon fiber, in 75Ar25CO2
V (V)	
Es
E
s
	​

 (kV/cm)	Gain 
M
M	
Q
Q (pC)	
Vpeak
V
peak
	​

 (mV)	Verdict
0	0.0	1.00e+00	1.84e-05	9.21e-05	not enough
100	13.4	1.00e+00	1.84e-05	9.21e-05	not enough
200	26.7	1.00e+00	1.84e-05	9.21e-05	not enough
300	40.1	1.05e+00	1.93e-05	9.66e-05	not enough
400	53.4	1.57e+00	2.89e-05	1.45e-04	not enough
500	66.8	2.54e+00	4.67e-05	2.34e-04	not enough
600	80.1	4.39e+00	8.08e-05	4.04e-04	not enough
700	93.5	8.02e+00	1.48e-04	7.38e-04	not enough
800	106.8	1.54e+01	2.84e-04	1.42e-03	not enough
900	120.2	3.07e+01	5.65e-04	2.82e-03	not enough
1000	133.5	6.37e+01	1.17e-03	5.87e-03	not enough
1100	146.9	1.36e+02	2.50e-03	1.25e-02	not enough
1200	160.2	3.01e+02	5.55e-03	2.77e-02	not enough
1300	173.6	6.84e+02	1.26e-02	6.29e-02	not enough
1400	186.9	1.59e+03	2.93e-02	1.47e-01	not enough
1500	200.3	3.79e+03	6.99e-02	3.49e-01	not enough
1600	213.6	9.25e+03	1.70e-01	8.51e-01	not enough
1700	227.0	2.30e+04	4.24e-01	2.12	not enough
1800	240.3	5.83e+04	1.07	5.37	barely visible
1900	253.7	1.51e+05	2.78	13.9	barely visible
2000	267.0	3.96e+05	7.30	36.5	reliable
2100	280.4	1.06e+06	19.5	97.5	reliable
2200	293.8	2.88e+06	53.0	265	reliable
Result
first likely visible: about 1800 V
good no-luck voltage: about 2000 V

So this one is basically unchanged from the muon-style estimate.

3) 7.7 µm core CF + 0.3 µm Ni, in air

For air, I do not treat this as a clean proportional-avalanche counter. The direct primary pulse from one realistic beta is just:

Qair=70.9 e≈1.136×10−17 C
Q
air
	​

=70.9e≈1.136×10
−17
 C
Qair≈1.136×10−5 pC
Q
air
	​

≈1.136×10
−5
 pC

So into 50 Ω with a 10 ns pulse,

Vpeak≈0.0568 μV
V
peak
	​

≈0.0568 μV

That is still far too small.

Using the same rough corona-onset estimate as before, the thin wire enters the dangerous air-corona neighborhood at roughly 1.4 kV, but that is not a clean proportional single-beta signal.

V (V)	
Es
E
s
	​

 (kV/cm)	
Q
Q (pC), no avalanche	
Vpeak
V
peak
	​

 (µV)	Verdict	Interpretation
0	0.0	1.136e-05	0.0568	not enough	below corona region
100	34.0	1.136e-05	0.0568	not enough	below corona region
200	67.9	1.136e-05	0.0568	not enough	below corona region
300	101.9	1.136e-05	0.0568	not enough	below corona region
400	135.9	1.136e-05	0.0568	not enough	below corona region
500	169.8	1.136e-05	0.0568	not enough	below corona region
600	203.8	1.136e-05	0.0568	not enough	below corona region
700	237.8	1.136e-05	0.0568	not enough	below corona region
800	271.7	1.136e-05	0.0568	not enough	below corona region
900	305.7	1.136e-05	0.0568	not enough	below corona region
1000	339.7	1.136e-05	0.0568	not enough	below corona region
1100	373.6	1.136e-05	0.0568	not enough	below corona region
1200	407.6	1.136e-05	0.0568	not enough	below corona region
1300	441.6	1.136e-05	0.0568	not enough	below corona region
1400	475.5	1.136e-05	0.0568	unstable corona region	may show discharge-like activity, not clean beta pulses
1500	509.5	1.136e-05	0.0568	unstable corona region	may show discharge-like activity, not clean beta pulses
1600	543.5	1.136e-05	0.0568	unstable corona region	may show discharge-like activity, not clean beta pulses
1700	577.4	1.136e-05	0.0568	unstable corona region	may show discharge-like activity, not clean beta pulses
Result
clean single-beta pulse on a scope in air: no
below ~1400 V: definitely no
above ~1400 V: you may enter air-corona behavior, but that is not a clean single-beta detection mode
4) 25 µm carbon fiber, in air

Same direct primary pulse as above:

Qair≈1.136×10−5 pC
Q
air
	​

≈1.136×10
−5
 pC
Vpeak≈0.0568 μV
V
peak
	​

≈0.0568 μV

Again, far too small.

With the same rough air-corona estimate, the 25 µm wire does not get near that region until roughly 2.1–2.2 kV.

V (V)	
Es
E
s
	​

 (kV/cm)	
Q
Q (pC), no avalanche	
Vpeak
V
peak
	​

 (µV)	Verdict	Interpretation
0	0.0	1.136e-05	0.0568	not enough	below corona region
100	13.4	1.136e-05	0.0568	not enough	below corona region
200	26.7	1.136e-05	0.0568	not enough	below corona region
300	40.1	1.136e-05	0.0568	not enough	below corona region
400	53.4	1.136e-05	0.0568	not enough	below corona region
500	66.8	1.136e-05	0.0568	not enough	below corona region
600	80.1	1.136e-05	0.0568	not enough	below corona region
700	93.5	1.136e-05	0.0568	not enough	below corona region
800	106.8	1.136e-05	0.0568	not enough	below corona region
900	120.2	1.136e-05	0.0568	not enough	below corona region
1000	133.5	1.136e-05	0.0568	not enough	below corona region
1100	146.9	1.136e-05	0.0568	not enough	below corona region
1200	160.2	1.136e-05	0.0568	not enough	below corona region
1300	173.6	1.136e-05	0.0568	not enough	below corona region
1400	186.9	1.136e-05	0.0568	not enough	below corona region
1500	200.3	1.136e-05	0.0568	not enough	below corona region
1600	213.6	1.136e-05	0.0568	not enough	below corona region
1700	227.0	1.136e-05	0.0568	not enough	below corona region
1800	240.3	1.136e-05	0.0568	not enough	below corona region
1900	253.7	1.136e-05	0.0568	not enough	below corona region
2000	267.0	1.136e-05	0.0568	not enough	below corona region
2100	280.4	1.136e-05	0.0568	not enough	below corona region
2200	293.8	1.136e-05	0.0568	unstable corona region	may show discharge-like activity, not clean beta pulses
Result
clean single-beta pulse on a scope in air: no
below ~2200 V: no
above ~2200 V: you are getting into unstable air behavior, not a clean proportional signal
Final answer

For a somewhat realistic single Sr-90/Y-90 beta event, the answer is:

Wire	Gas	First likely visible	Comfortable / reliable
7.7 µm core CF + 0.3 µm Ni	75Ar25CO2	1600 V	1700 V
25 µm carbon fiber	75Ar25CO2	1800 V	2000 V
7.7 µm core CF + 0.3 µm Ni	Air	no clean proportional beta pulse	only unstable corona region ~1400 V+
25 µm carbon fiber	Air	no clean proportional beta pulse	only unstable corona region ~2200 V+
Most important physical takeaway

A single realistic Sr-90/Y-90 beta does not give you an enormously larger pulse than the single cosmic-muon estimate from before. For a ~1 cm gas path, the number of primary ion pairs stays around tens to a bit over one hundred, so the scope-visibility voltages stay in essentially the same range.

If you want the next step, the most useful improvement would be a source-geometry-aware beta calculation: source window thickness, source-to-wire distance, air gap, collimation, and actual beta angle/track-length distribution. That can shift the threshold more meaningfully than swapping “muon” to “beta” in the simple 1 cm single-track model.

can you please go over the exact calculations steps for a single voltage point of say 2000V for both wires and gases for a cosmic muon

I’m reusing the exact same model and assumptions as the earlier muon estimate, and I’ll show all four 2000 V cases explicitly so you can see where every number comes from.

Thought for 1m 10s

Yes — using the same cosmic-muon model and same scope model as before, I can walk through the full calculation at one voltage point: 2000 V for all four cases.

Fixed assumptions

I am keeping the same assumptions from the earlier muon estimate so the numbers stay consistent:

Geometry

effective outer grounded cylinder radius:

b=5 mm=0.5 cm
b=5 mm=0.5 cm
Wire 1: thin Ni-coated CF wire
CF core diameter = 
7.7 μm
7.7 μm
Ni coating = 
0.3 μm
0.3 μm on each side

total diameter:

d=7.7+2(0.3)=8.3 μm
d=7.7+2(0.3)=8.3 μm

wire radius:

a=4.15 μm=4.15×10−4 cm
a=4.15 μm=4.15×10
−4
 cm
Wire 2: 25 µm carbon fiber wire

diameter:

d=25 μm
d=25 μm

radius:

a=12.5 μm=1.25×10−3 cm
a=12.5 μm=1.25×10
−3
 cm
Cosmic-muon ionization assumptions

These are the same working numbers I used before:

in 75Ar25CO2:

N0=130 primary electrons
N
0
	​

=130 primary electrons

survival factor:

fsurv=0.95
f
surv
	​

=0.95

in air:

N0=70 primary electrons
N
0
	​

=70 primary electrons

and for the clean-signal estimate I take:

M=1
M=1

because I am not treating air as a stable proportional-avalanche case

Scope/readout model

Same as before:

termination:

R=50 Ω
R=50 Ω

pulse width:

τ=10 ns=1.0×10−8 s
τ=10 ns=1.0×10
−8
 s

Then:

Vpeak=QτR
V
peak
	​

=
τ
Q
	​

R

with electron charge:

e=1.602×10−19 C
e=1.602×10
−19
 C
Shared electrostatic formula

For a cylindrical proportional-counter model, the wire surface field is

Es=Valn⁡(b/a)
E
s
	​

=
aln(b/a)
V
	​


We now evaluate this at

V=2000 V
V=2000 V
Case 1: 2000 V, thin Ni-coated CF wire, 75Ar25CO2
Step 1: geometric log factor
ln⁡(b/a)=ln⁡(0.54.15×10−4)
ln(b/a)=ln(
4.15×10
−4
0.5
	​

)
0.54.15×10−4=1204.82
4.15×10
−4
0.5
	​

=1204.82
ln⁡(b/a)=ln⁡(1204.82)=7.094
ln(b/a)=ln(1204.82)=7.094
Step 2: wire surface field
Es=2000(4.15×10−4)(7.094)
E
s
	​

=
(4.15×10
−4
)(7.094)
2000
	​


First compute the denominator:

(4.15×10−4)(7.094)=2.944×10−3 cm
(4.15×10
−4
)(7.094)=2.944×10
−3
 cm

So

Es=20002.944×10−3=6.793×105 V/cm
E
s
	​

=
2.944×10
−3
2000
	​

=6.793×10
5
 V/cm
Es=679.3 kV/cm
E
s
	​

=679.3 kV/cm
Step 3: gas-gain threshold parameter 
V0
V
0
	​


Using the same Diethorn-style surrogate as before:

V0=p a ln⁡(b/a)(Emin⁡p)
V
0
	​

=paln(b/a)(
p
E
min
	​

	​

)

with

p=760 Torr,Emin⁡p=50 V/(cm\cdotpTorr)
p=760 Torr,
p
E
min
	​

	​

=50 V/(cm\cdotpTorr)

So:

V0=760(4.15×10−4)(7.094)(50)
V
0
	​

=760(4.15×10
−4
)(7.094)(50)
V0=111.9 V
V
0
	​

=111.9 V
Step 4: gas gain 
M
M

Using

ln⁡M=Vln⁡(b/a)ln⁡2ΔVln⁡(VV0)
lnM=
ln(b/a)
V
	​

ΔV
ln2
	​

ln(
V
0
	​

V
	​

)

with

ΔV=35 V
ΔV=35 V

Substitute:

ln⁡M=20007.094⋅ln⁡235⋅ln⁡(2000111.9)
lnM=
7.094
2000
	​

⋅
35
ln2
	​

⋅ln(
111.9
2000
	​

)

Now compute each factor:

20007.094=281.93
7.094
2000
	​

=281.93
ln⁡235=0.693135=0.01980
35
ln2
	​

=
35
0.6931
	​

=0.01980
2000111.9=17.87
111.9
2000
	​

=17.87
ln⁡(17.87)=2.883
ln(17.87)=2.883

So

ln⁡M=281.93×0.01980×2.883
lnM=281.93×0.01980×2.883
ln⁡M=16.10
lnM=16.10

Therefore

M=e16.10=9.82×106
M=e
16.10
=9.82×10
6
Step 5: total collected charge
Q=N0fsurveM
Q=N
0
	​

f
surv
	​

eM
Q=130×0.95×(1.602×10−19)×(9.82×106)
Q=130×0.95×(1.602×10
−19
)×(9.82×10
6
)

First:

130×0.95=123.5
130×0.95=123.5

Then:

123.5×1.602×10−19=1.978×10−17 C
123.5×1.602×10
−19
=1.978×10
−17
 C

Then:

Q=(1.978×10−17)(9.82×106)
Q=(1.978×10
−17
)(9.82×10
6
)
Q=1.94×10−10 C
Q=1.94×10
−10
 C

In pC:

Q=194 pC
Q=194 pC
Step 6: peak scope voltage
Vpeak=QτR
V
peak
	​

=
τ
Q
	​

R
Vpeak=1.94×10−101.0×10−8×50
V
peak
	​

=
1.0×10
−8
1.94×10
−10
	​

×50
Vpeak=0.971 V
V
peak
	​

=0.971 V
Vpeak=971 mV
V
peak
	​

=971 mV
Result

At 2000 V, for the thin Ni-coated wire in 75Ar25CO2:

surface field:

679.3 kV/cm
679.3 kV/cm

gain:

9.82×106
9.82×10
6

collected charge:

194 pC
194 pC

peak signal:

971 mV
971 mV

Conclusion: comfortably visible, far above threshold.

Case 2: 2000 V, 25 µm carbon fiber wire, 75Ar25CO2
Step 1: geometric log factor
ln⁡(b/a)=ln⁡(0.51.25×10−3)
ln(b/a)=ln(
1.25×10
−3
0.5
	​

)
0.51.25×10−3=400
1.25×10
−3
0.5
	​

=400
ln⁡(b/a)=ln⁡(400)=5.991
ln(b/a)=ln(400)=5.991
Step 2: wire surface field
Es=2000(1.25×10−3)(5.991)
E
s
	​

=
(1.25×10
−3
)(5.991)
2000
	​


Denominator:

(1.25×10−3)(5.991)=7.489×10−3 cm
(1.25×10
−3
)(5.991)=7.489×10
−3
 cm

So

Es=20007.489×10−3=2.670×105 V/cm
E
s
	​

=
7.489×10
−3
2000
	​

=2.670×10
5
 V/cm
Es=267.0 kV/cm
E
s
	​

=267.0 kV/cm
Step 3: 
V0
V
0
	​

V0=760(1.25×10−3)(5.991)(50)
V
0
	​

=760(1.25×10
−3
)(5.991)(50)
V0=284.6 V
V
0
	​

=284.6 V
Step 4: gas gain 
M
M
ln⁡M=20005.991⋅ln⁡235⋅ln⁡(2000284.6)
lnM=
5.991
2000
	​

⋅
35
ln2
	​

⋅ln(
284.6
2000
	​

)

Compute factors:

20005.991=333.81
5.991
2000
	​

=333.81
ln⁡235=0.01980
35
ln2
	​

=0.01980
2000284.6=7.03
284.6
2000
	​

=7.03
ln⁡(7.03)=1.950
ln(7.03)=1.950

So

ln⁡M=333.81×0.01980×1.950
lnM=333.81×0.01980×1.950
ln⁡M=12.89
lnM=12.89

Thus

M=e12.89=3.96×105
M=e
12.89
=3.96×10
5
Step 5: collected charge
Q=130×0.95×(1.602×10−19)×(3.96×105)
Q=130×0.95×(1.602×10
−19
)×(3.96×10
5
)

We already had:

130×0.95×1.602×10−19=1.978×10−17 C
130×0.95×1.602×10
−19
=1.978×10
−17
 C

So

Q=(1.978×10−17)(3.96×105)
Q=(1.978×10
−17
)(3.96×10
5
)
Q=7.84×10−12 C
Q=7.84×10
−12
 C

In pC:

Q=7.84 pC
Q=7.84 pC
Step 6: peak scope voltage
Vpeak=7.84×10−121.0×10−8×50
V
peak
	​

=
1.0×10
−8
7.84×10
−12
	​

×50
Vpeak=0.0392 V
V
peak
	​

=0.0392 V
Vpeak=39.2 mV
V
peak
	​

=39.2 mV
Result

At 2000 V, for the 25 µm CF wire in 75Ar25CO2:

surface field:

267.0 kV/cm
267.0 kV/cm

gain:

3.96×105
3.96×10
5

collected charge:

7.84 pC
7.84 pC

peak signal:

39.2 mV
39.2 mV

Conclusion: clearly visible and into the “reliable” region.

Case 3: 2000 V, thin Ni-coated CF wire, air

Here I use the same logic as before:

a cosmic muon gives about

N0=70
N
0
	​

=70

primary electrons in the assumed path

for clean signal estimation in air, I do not apply stable proportional avalanche gain

so:

M=1
M=1
Step 1: field at the wire

This is the same geometry as Case 1, so:

Es=679.3 kV/cm
E
s
	​

=679.3 kV/cm
Step 2: collected charge
Q=N0e
Q=N
0
	​

e
Q=70×1.602×10−19
Q=70×1.602×10
−19
Q=1.121×10−17 C
Q=1.121×10
−17
 C

In pC:

Q=1.121×10−5 pC
Q=1.121×10
−5
 pC
Step 3: peak scope voltage
Vpeak=1.121×10−171.0×10−8×50
V
peak
	​

=
1.0×10
−8
1.121×10
−17
	​

×50
Vpeak=5.61×10−8 V
V
peak
	​

=5.61×10
−8
 V
Vpeak=0.0561 μV
V
peak
	​

=0.0561 μV
Result

At 2000 V, for the thin Ni-coated wire in air:

surface field:

679.3 kV/cm
679.3 kV/cm

clean-signal charge:

1.12×10−17 C
1.12×10
−17
 C

peak signal:

0.0561 μV
0.0561 μV

Conclusion: the clean direct muon pulse is far too small for a normal scope.

Important caveat

At this field, the wire is in the neighborhood where air-corona / unstable behavior may start to matter. So if you actually see large pulses in air near this voltage, they are more likely due to corona / discharge-like processes than a clean proportional muon pulse.

Case 4: 2000 V, 25 µm carbon fiber wire, air

Again:

primary electrons:

N0=70
N
0
	​

=70

no stable proportional gain assumed:

M=1
M=1
Step 1: field at the wire

This is the same geometry as Case 2, so:

Es=267.0 kV/cm
E
s
	​

=267.0 kV/cm
Step 2: collected charge

Exactly the same direct primary charge as Case 3:

Q=70×1.602×10−19=1.121×10−17 C
Q=70×1.602×10
−19
=1.121×10
−17
 C
Q=1.121×10−5 pC
Q=1.121×10
−5
 pC
Step 3: peak scope voltage
Vpeak=1.121×10−171.0×10−8×50=5.61×10−8 V
V
peak
	​

=
1.0×10
−8
1.121×10
−17
	​

×50=5.61×10
−8
 V
Vpeak=0.0561 μV
V
peak
	​

=0.0561 μV
Result

At 2000 V, for the 25 µm CF wire in air:

surface field:

267.0 kV/cm
267.0 kV/cm

clean-signal charge:

1.12×10−17 C
1.12×10
−17
 C

peak signal:

0.0561 μV
0.0561 μV

Conclusion: also far too small for normal scope visibility.

In this case, unlike the thin wire, 2000 V is still less suggestive of immediate air-corona onset, so this one is even more straightforwardly “not enough” for a clean direct muon pulse.

Final comparison at 2000 V
Wire	Gas	
Es
E
s
	​

 (kV/cm)	Gain 
M
M	Charge 
Q
Q	
Vpeak
V
peak
	​

	What that means
8.3 µm total dia. Ni-coated CF	75Ar25CO2	679.3	
9.82×106
9.82×10
6
	194 pC	971 mV	extremely visible
25 µm CF	75Ar25CO2	267.0	
3.96×105
3.96×10
5
	7.84 pC	39.2 mV	clearly visible
8.3 µm total dia. Ni-coated CF	air	679.3	1	
1.12×10−17
1.12×10
−17
 C	0.0561 µV	not visible as clean muon pulse
25 µm CF	air	267.0	1	
1.12×10−17
1.12×10
−17
 C	0.0561 µV	not visible as clean muon pulse
Main takeaway

At 2000 V for a cosmic muon:

both wires in 75Ar25CO2 should give visible signals
the thin Ni-coated wire is much stronger because its surface field is much higher, so its gain is much higher
in air, the clean direct muon signal remains tiny for both wires; if you see something large for the thin wire, it is likely because you have moved into air-corona / unstable discharge behavior, not because you are running a nice proportional counter

The next most useful follow-up would be to do the same single-point worked derivation at 1700 V and 1800 V, since those are closer to the practical threshold region.