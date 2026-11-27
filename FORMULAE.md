# RadioCov Physics & RF Propagation Mathematical Formulations

This document provides the complete, rigorous mathematical formulations, physical models, and algorithms implemented in the **RadioCov** library and coverage engine. 

All formulations follow recognized international standards, notably **ITU-R Recommendation P.526** (Propagation by diffraction), **ICAO Annex 10** (Aeronautical Telecommunications), and classical electrodynamics and geodetic reference systems (**WGS-84**).

---

## Table of Contents
1. [Geodesics & Earth Geometry](#1-geodesics--earth-geometry)
2. [Atmospheric Refraction & Effective Earth Radius](#2-atmospheric-refraction--effective-earth-radius)
3. [Spherical Earth Bulge & Direct Ray Geometry](#3-spherical-earth-bulge--direct-ray-geometry)
4. [Fresnel Zone Ellipsoid & Clearance Ratio](#4-fresnel-zone-ellipsoid--clearance-ratio)
5. [Diffraction Modeling (ITU-R P.526-15)](#5-diffraction-modeling-itu-r-p526-15)
6. [Free Space Path Loss (FSPL)](#6-free-space-path-loss-fspl)
7. [Link Budget & Maximum Allowable Path Loss (MAPL)](#7-link-budget--maximum-allowable-path-loss-mapl)
8. [Sub-Meter Obstacle Intersection & Blockage Distance](#8-sub-meter-obstacle-intersection--blockage-distance)
9. [Compound Near-Field Masking (DEM Position Confusion)](#9-compound-near-field-masking-dem-position-confusion)
10. [Volumetric Airspace Discretization (1,000-ft Voxels)](#10-volumetric-airspace-discretization-1000-ft-voxels)
11. [Summary Table of Physical Constants](#11-summary-table-of-physical-constants)

---

## 1. Geodesics & Earth Geometry

Transmitters, receivers, and terrain elevation samples are defined in the **World Geodetic System 1984 (WGS-84)** coordinate frame with latitude $\phi$, longitude $\lambda$, and height above mean sea level $h_{\text{AMSL}}$.

### 1.1 Great-Circle Distance (Haversine Formulation)

Between a transmitter $(\phi_1, \lambda_1)$ and receiver $(\phi_2, \lambda_2)$, the central angular separation $\Delta \sigma$ is:

$$\Delta \sigma = 2 \arcsin \left( \sqrt{\sin^2\left(\frac{\Delta \phi}{2}\right) + \cos \phi_1 \cos \phi_2 \sin^2\left(\frac{\Delta \lambda}{2}\right)} \right)$$

where:
- $\Delta \phi = \phi_2 - \phi_1$ (latitude difference in radians)
- $\Delta \lambda = \lambda_2 - \lambda_1$ (longitude difference in radians)
- $R_0 = 6,371,000 \text{ m}$ (mean Earth spherical radius)

The surface geodesic distance $d$ along the mean sphere is:

$$d = R_0 \cdot \Delta \sigma$$

### 1.2 Forward Azimuth (Initial Bearing)

The initial bearing $\theta \in [0, 2\pi)$ from the transmitter to the receiver along the great circle is:

$$\theta = \operatorname{atan2}\Big(\sin \Delta \lambda \cos \phi_2, \; \cos \phi_1 \sin \phi_2 - \sin \phi_1 \cos \phi_2 \cos \Delta \lambda\Big) \pmod{2\pi}$$

### 1.3 Direct Geodetic Radial Waypoint

Given a transmitter location $(\phi_1, \lambda_1)$, azimuth $\theta$, and distance $s \le d$:

$$\phi(s) = \arcsin\left(\sin \phi_1 \cos \left(\frac{s}{R_0}\right) + \cos \phi_1 \sin \left(\frac{s}{R_0}\right) \cos \theta\right)$$

$$\lambda(s) = \lambda_1 + \operatorname{atan2}\left(\sin \theta \sin \left(\frac{s}{R_0}\right) \cos \phi_1, \; \cos \left(\frac{s}{R_0}\right) - \sin \phi_1 \sin \phi_1 \sin \phi(s)\right)$$

---

## 2. Atmospheric Refraction & Effective Earth Radius

In the lower troposphere, atmospheric pressure, temperature, and water vapor decrease with altitude. Consequently, the radio refractive index $n$ decreases with height above ground:

$$\frac{dn}{dh} \approx -40 \times 10^{-6} \text{ km}^{-1} = -4.0 \times 10^{-8} \text{ m}^{-1}$$

This negative vertical refractivity gradient bends propagating radio waves downward toward the Earth's surface. 

### 2.1 The Equivalent $k$-Factor

By Schelleng, Burrows, and Ferrell's transformation, ray paths can be modeled as straight lines if the physical radius of the Earth $R_0$ is replaced by an **effective Earth radius** $R_e'$:

$$R_e' = k \cdot R_0$$

where the atmospheric bending factor $k$ is given by:

$$k = \frac{1}{1 + R_0 \dfrac{dn}{dh}}$$

### 2.2 Standard Tropospheric Value

Under standard atmospheric conditions (ITU-R P.453):

$$k = \frac{4}{3} \approx 1.333333$$

$$R_e' = \frac{4}{3} \times 6,371,000 \text{ m} \approx 8,494,667 \text{ m}$$

RadioCov allows user configuration of $k$ from sub-refraction ($k < 1.0$, ducting/trapping avoidance) to super-refraction ($k > 1.333$).

---

## 3. Spherical Earth Bulge & Direct Ray Geometry

### 3.1 Earth Bulge Formulation

For an RF link of total horizontal distance $d = d_1 + d_2$, where an obstacle or intermediate evaluation point is located at distance $d_1$ from the transmitter and $d_2$ from the receiver, the geometric Earth bulge $h_{\text{bulge}}$ projecting upward into the path is:

$$h_{\text{bulge}}(d_1, d_2) = \frac{d_1 \cdot d_2}{2 \cdot R_e'} = \frac{d_1 \cdot d_2}{2 \cdot k \cdot R_0}$$

At the path midpoint ($d_1 = d_2 = d / 2$):

$$h_{\text{bulge,max}} = \frac{d^2}{8 \cdot k \cdot R_0}$$

### 3.2 Direct Ray Line-of-Sight Altitude

Let:
- $h_{\text{tx}}$ be the transmitter antenna altitude AMSL ($h_{\text{tx,ground}} + h_{\text{tx,mast}}$).
- $h_{\text{rx}}$ be the receiver antenna altitude AMSL ($h_{\text{rx,ground}} + h_{\text{rx,mast}}$).
- $s \in [0, d]$ be the distance from the transmitter along the great circle ($d_1 = s, \; d_2 = d - s$).

The geometric ray altitude $h_{\text{ray}}(s)$ above mean sea level is:

$$h_{\text{ray}}(s) = h_{\text{tx}} + \frac{s}{d} \Big(h_{\text{rx}} - h_{\text{tx}}\Big) - h_{\text{bulge}}(s, d - s)$$

$$h_{\text{ray}}(s) = h_{\text{tx}} + \frac{s}{d} \Big(h_{\text{rx}} - h_{\text{tx}}\Big) - \frac{s (d - s)}{2 \cdot k \cdot R_0}$$

### 3.3 Elevation Angle

The apparent elevation angle $\theta_{\text{elev}}$ from the transmitter to the receiver over curved Earth:

$$\Delta h_{\text{curv}} = \frac{d^2}{2 \cdot k \cdot R_0}$$

$$\theta_{\text{elev}} = \arctan \left( \frac{(h_{\text{rx}} - h_{\text{tx}}) - \Delta h_{\text{curv}}}{d} \right)$$

---

## 4. Fresnel Zone Ellipsoid & Clearance Ratio

### 4.1 RF Wavelength

Given carrier frequency $f$ in Hertz and the speed of light $c = 299,792,458 \text{ m/s}$:

$$\lambda = \frac{c}{f}$$

### 4.2 Fresnel Zone Radius ($n$-th Order)

The boundary of the $n$-th Fresnel zone is an ellipsoid of revolution with foci at the transmitter and receiver antennas. The radius $F_n(s)$ at distance $d_1 = s$ and $d_2 = d - s$ is:

$$F_n(s) = \sqrt{\frac{n \cdot \lambda \cdot d_1 \cdot d_2}{d_1 + d_2}} = \sqrt{\frac{n \cdot \lambda \cdot s \cdot (d - s)}{d}}$$

For the **First Fresnel Zone ($n = 1$)**:

$$F_1(s) = \sqrt{\frac{\lambda \cdot s \cdot (d - s)}{d}}$$

The maximum First Fresnel zone radius occurs at the path midpoint ($s = d / 2$):

$$F_{1,\max} = \frac{1}{2} \sqrt{\lambda \cdot d}$$

### 4.3 Terrain Clearance & Clearance Ratio

Let $h_{\text{terrain}}(s)$ be the digital elevation model (DEM) surface elevation at distance $s$. The absolute obstacle clearance $C(s)$ is:

$$C(s) = h_{\text{ray}}(s) - h_{\text{terrain}}(s)$$

The normalized First Fresnel clearance ratio is:

$$\text{Clearance Ratio}(s) = \frac{C(s)}{F_1(s)}$$

- **Optical Line of Sight (LoS)**:
  $$\forall s \in (0, d): \quad C(s) > 0$$
- **Standard Unobstructed Radio LoS (Sub-refractive clearance)**:
  $$\min_{s \in (0, d)} \frac{C(s)}{F_1(s)} \ge 0.60$$
  A clearance of $0.60 \cdot F_1$ guarantees essentially zero diffraction loss ($\le 0 \text{ dB}$) in the standard troposphere.
- **Deeply Blocked / Non-LoS (NLoS)**:
  $$\exists s \in (0, d): \quad C(s) < 0 \quad \iff \quad h_{\text{terrain}}(s) > h_{\text{ray}}(s)$$

---

## 5. Diffraction Modeling (ITU-R P.526-15)

When terrain penetrates into the First Fresnel Zone ($C(s) < 0.6 F_1(s)$) or occludes the direct ray ($C(s) < 0$), diffraction occurs around the obstruction.

### 5.1 Dimensionless Fresnel-Kirchhoff Parameter $v$

The obstacle penetration height above line of sight is:

$$h_{\text{obs}}(s) = -C(s) = h_{\text{terrain}}(s) - h_{\text{ray}}(s)$$

The dimensionless Fresnel-Kirchhoff diffraction parameter $v(s)$ is defined as:

$$v(s) = h_{\text{obs}}(s) \sqrt{\frac{2 (d_1 + d_2)}{\lambda \cdot d_1 \cdot d_2}} = - \frac{C(s)}{F_1(s)} \sqrt{2}$$

- When the path is **clear** ($C > 0$): $v < 0$.
- At grazing incidence ($C = 0$): $v = 0$.
- When the path is **obstructed** ($C < 0$): $v > 0$.

### 5.2 Single Knife-Edge Diffraction Loss $J(v)$

According to **ITU-R Recommendation P.526-15**, the diffraction attenuation $J(v)$ in decibels is approximated piecewise:

$$J(v) = \begin{cases}
0 & \text{for } v \le -0.7 \\
6.02 + 9.11 \, v - 1.27 \, v^2 & \text{for } -0.7 < v \le 1.0 \\
12.953 + 20 \log_{10}(v) & \text{for } 1.0 < v \le 2.4 \\
16.0 + 20 \log_{10}(v) & \text{for } v > 2.4
\end{cases}$$

For the critical transition at grazing incidence ($v = 0$):
$$J(0) = 6.02 \text{ dB}$$
representing the theoretical $6 \text{ dB}$ signal voltage halving at the geometric shadow boundary of a semi-infinite screen.

---

## 6. Free Space Path Loss (FSPL)

### 6.1 Friis Transmission Formula

In an ideal, unbounded, isotropic medium without obstacles, the power received $P_{\text{rx}}$ at 3D slant distance $d_{\text{3D}}$ is governed by the Friis transmission equation:

$$P_{\text{rx}} = P_{\text{tx}} \cdot G_{\text{tx}} \cdot G_{\text{rx}} \cdot \left(\frac{\lambda}{4 \pi d_{\text{3D}}}\right)^2$$

where $d_{\text{3D}} = \sqrt{d^2 + (h_{\text{rx}} - h_{\text{tx}})^2}$.

### 6.2 Logarithmic Free Space Path Loss

The Free Space Path Loss $\text{FSPL}$ in decibels ($\text{dB}$) is:

$$\text{FSPL}(\text{dB}) = 10 \log_{10} \left( \frac{4 \pi d_{\text{3D}}}{\lambda} \right)^2 = 20 \log_{10}(d_{\text{3D}}) + 20 \log_{10}(f) + 20 \log_{10}\left(\frac{4 \pi}{c}\right)$$

Evaluating the constant:

$$20 \log_{10}\left(\frac{4 \pi}{299,792,458}\right) \approx -147.55216$$

Thus:
$$\text{FSPL}(d_{\text{meters}}, f_{\text{Hz}}) = 20 \log_{10}(d) + 20 \log_{10}(f) - 147.55216 \text{ dB}$$

Equivalently, with distance in kilometers $d_{\text{km}}$ and frequency in Megahertz $f_{\text{MHz}}$:

$$\text{FSPL}(d_{\text{km}}, f_{\text{MHz}}) = 32.44 + 20 \log_{10}(d_{\text{km}}) + 20 \log_{10}(f_{\text{MHz}})$$

### 6.3 Total Link Path Loss

The total path attenuation $L_{\text{total}}$ combining free-space spreading and knife-edge diffraction is:

$$L_{\text{total}}(\text{dB}) = \text{FSPL}(\text{dB}) + J(v_{\max})(\text{dB}) + L_{\text{misc}}(\text{dB})$$

where:
$$v_{\max} = \max_{s \in (0, d)} v(s)$$
and $L_{\text{misc}}$ accounts for system margins, connector losses, or polarization mismatch.

---

## 7. Link Budget & Maximum Allowable Path Loss (MAPL)

The link budget determines whether a specific RF technology can reliably close the communication or surveillance link over the modeled path.

### 7.1 Effective Isotropic Radiated Power (EIRP)

$$\text{EIRP}(\text{dBm}) = P_{\text{tx}}(\text{dBm}) + G_{\text{tx}}(\text{dBi}) - L_{\text{cable,tx}}(\text{dB})$$

### 7.2 Maximum Allowable Path Loss (MAPL)

The maximum path attenuation the link can tolerate before the received signal drops below the receiver demodulation threshold plus fade margin:

$$\text{MAPL}(\text{dB}) = \text{EIRP}(\text{dBm}) + G_{\text{rx}}(\text{dBi}) - L_{\text{cable,rx}}(\text{dB}) - P_{\text{rx,sens}}(\text{dBm}) - M_{\text{fade}}(\text{dB})$$

where:
- $P_{\text{tx}}$: Transmitter output power ($\text{dBm}$). Note: $P_{\text{dBm}} = 10 \log_{10}(P_{\text{W}} \cdot 1000)$.
- $G_{\text{tx}}, G_{\text{rx}}$: Antenna gains ($\text{dBi}$).
- $L_{\text{cable,tx}}, L_{\text{cable,rx}}$: Feeder and connector insertion losses ($\text{dB}$).
- $P_{\text{rx,sens}}$: Receiver sensitivity threshold for target Bit Error Rate (BER) or detection probability ($\text{dBm}$).
- $M_{\text{fade}}$: Log-normal shadow and multipath fade margin ($\text{dB}$).

### 7.3 Link Margin

The link margin $\Delta M$ is the excess power available above the receiver sensitivity threshold:

$$\Delta M(\text{dB}) = \text{MAPL}(\text{dB}) - L_{\text{total}}(\text{dB})$$

- **Link Closed (Usable Service)**: $\Delta M \ge 0 \text{ dB}$
- **Link Failed (Out of Service)**: $\Delta M < 0 \text{ dB}$

---

## 8. Sub-Meter Obstacle Intersection & Blockage Distance

When a radio path is obstructed, determining the exact physical distance where the line-of-sight ray enters the terrain is critical for siting and obstacle clearance.

### 8.1 Continuous Zero-Crossing Root Finding

Along a radial path sampled at discrete intervals $s_i$ ($i = 0, 1, \dots, N$):

$$\Delta h_i = h_{\text{ray}}(s_i) - h_{\text{terrain}}(s_i)$$

A terrain penetration event occurs at the first interval $[s_k, s_{k+1}]$ where:

$$\Delta h_k \ge 0 \quad \text{and} \quad \Delta h_{k+1} < 0$$

Assuming piecewise-linear terrain between DEM raster cells, the exact blockage distance $d_{\text{block}}$ is found by sub-meter linear interpolation:

$$t = \frac{\Delta h_k}{\Delta h_k - \Delta h_{k+1}} \in [0, 1]$$

$$d_{\text{block}} = s_k + t \cdot (s_{k+1} - s_k)$$

The exact terrain intersection altitude AMSL is:

$$h_{\text{block}} = h_{\text{terrain}}(s_k) + t \cdot \Big(h_{\text{terrain}}(s_{k+1}) - h_{\text{terrain}}(s_k)\Big)$$

---

## 9. Compound Near-Field Masking (DEM Position Confusion)

In real-world deployments, radio transmitters are mounted on steel lattice towers, mast structures, or rooftops located within a fenced facility compound. High-resolution Digital Elevation Models (such as the 25-meter EU-DEM) represent bare ground or surface canopies and can experience sub-pixel lateral positioning uncertainty (e.g., $\pm 10\text{--}25\text{ m}$).

If the mast coordinate falls on the edge of a DEM pixel whose center represents an adjacent elevated ridge or embankment, the ray path could register an immediate false blockage within tens of meters of the transmitter.

### 9.1 Compound Exclusion Mask

To eliminate local positioning artifacts, RadioCov provides a configurable **Compound / Position Confusion Radius** $R_{\text{compound}} \in [25\text{ m}, 100\text{ m}]$.

For all distance evaluations $s \in [0, d]$:

$$\text{Evaluate Obstacle}(s) = \begin{cases}
\text{False (Suppressed)} & \text{if } s \le R_{\text{compound}} \\
\text{True (Evaluated)} & \text{if } s > R_{\text{compound}}
\end{cases}$$

This ensures that only actual geographic obstacles outside the transmitter compound affect line-of-sight and Fresnel clearance calculations.

---

## 10. Volumetric Airspace Discretization (1,000-ft Voxels)

RadioCov quantizes the surrounding 3D airspace into standardized volumetric units of **1,000 feet** vertical thickness, matching international aeronautical flight level structure (ICAO Annex 2).

### 10.1 Vertical Quantization

Given minimum and maximum evaluation altitudes $Alt_{\min}$ and $Alt_{\max}$ in feet:

$$h_k = (k \cdot 1000) \times 0.3048 \text{ meters}, \quad k \in [\lfloor Alt_{\min}/1000 \rfloor, \; \lceil Alt_{\max}/1000 \rceil]$$

### 10.2 Cylindrical Polar Sampling & Geometric Transformation

The volume surrounding the transmitter is discretized in polar coordinates $(r_i, \theta_j, z_k)$:
- Radials: $\theta_j = j \cdot \Delta \theta$, with $\Delta \theta = \dfrac{360^\circ}{N_{\text{radials}}}$ (typically 72 to 360 radials).
- Range: $r_i = i \cdot \Delta r$, with $\Delta r = \dfrac{R_{\max}}{N_{\text{steps}}}$.
- Altitude: $z_k = h_k$.

For 3D WebGL / Three.js hardware acceleration, cylindrical coordinates are transformed to Cartesian coordinates $(X, Y, Z)$ centered at the transmitter:

$$X_{i,j} = r_i \cdot \sin \theta_j$$

$$Y_{i,j} = r_i \cdot \cos \theta_j$$

$$Z_{i,j,k} = \Big(z_k - h_{\text{tx}}\Big) \cdot E_z$$

where $E_z$ is the user-selected **vertical exaggeration factor** (typically $1.0\times$ to $10.0\times$).

---

## 11. Summary Table of Physical Constants

| Symbol | Parameter Description | Value / Units | Reference Standard |
| :--- | :--- | :--- | :--- |
| $c$ | Speed of light in vacuum | $299,792,458 \text{ m/s}$ | SI standard |
| $R_0$ | Mean Earth spherical radius | $6,371,000 \text{ m}$ | WGS-84 / IUGG |
| $k$ | Standard atmospheric refraction factor | $4/3 \approx 1.333333$ | ITU-R P.453 / P.834 |
| $dn/dh$ | Standard tropospheric refractivity gradient | $-40 \times 10^{-6} \text{ km}^{-1}$ | ITU-R P.453 |
| $R_e'$ | Effective Earth radius ($k \cdot R_0$) | $\approx 8,494,667 \text{ m}$ | Schelleng / ITU-R |
| $\text{FT\_TO\_M}$ | International foot to meter factor | $0.3048 \text{ m/ft}$ | ISO standard |
| $\Delta h_{\text{cube}}$ | Standard volumetric altitude step | $1,000 \text{ ft} = 304.8 \text{ m}$ | ICAO Flight Level |
| $J(0)$ | Shadow boundary knife-edge diffraction | $6.02 \text{ dB}$ | ITU-R P.526-15 |
| $C/F_1$ | Standard radio LoS clearance threshold | $0.60$ | ITU-R P.526 |
