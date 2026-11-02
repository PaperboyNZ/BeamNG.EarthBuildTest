# Active regional architecture: runtime and visual references

The source implementation activates 64 regional profiles in building generator v2 (building schema 16). Geographic selection uses source coordinates; a zoning import is not required. The matching playtest is `BeamNG.Earth-v2-regional-themes-balanced-20261101`; native BeamNG visual and performance acceptance remains pending.

## Geographic selection

The bundled public-domain Natural Earth v5.1.2 country/map-unit and province polygons route buildings to 64 regional profiles. There are 477 routing features: country defaults, provincial overrides, clipped authored climate transitions and a documented Davis Station locality patch. Explicit regional overlays have priority. Conflicting overlays or equally specific borders remain unresolved. A 500 m, locally scaled shoreline allowance handles generalized coastlines only when the result is unambiguous. Ocean points are not assigned to distant countries.

Administrative borders and authored climatic divisions approximate architectural geography; they are not exact cultural boundaries. Small missing islands, reclamation beyond 500 m and disputed/transition areas can require a more precise local override. Source URLs and hashes are embedded in the map. [Natural Earth data](https://www.naturalearthdata.com/downloads/10m-cultural-vectors/10m-admin-1-states-provinces/) are [public domain](https://www.naturalearthdata.com/about/terms-of-use/).

## Visible implementation

Every profile supplies weighted facade/roof materials, a wall-colour palette, roof-form and pitch defaults, window width/bay/sill/head proportions, reveal/frame dimensions, trim/accent colours and a compatible subset of sash bars, shutters, lintels, floor bands, timber strips, vertical shade screens and window canopies. Stable per-building ordinary, local-detail and contemporary expressions avoid applying identical decoration to every house. These are authored choices, not measured style prevalence.

The profiles now select among 14 authored facade grammars. They adjust grouped, vertical, horizontal or regular openings and add bounded piers, beams, cornices, recessed panels and material zones within existing walls. Deep reveals and arched or segmental openings are supported; at most 32 arches are emitted per building. Arch masks cover the rectangular pane corners, with simplified lite geometry. Recessed panels suggest loggias or verandas but do not create walkable space. Base and upper material zones apply only to fallback cladding without observed facade colour.

Five optional roof variants—gambrel, mansard, saltbox, shed and broad-eave—augment the standard flat, gabled and hipped forms. Variant geometry is confined to the original footprint and applies only to compatible rectangular pitched roofs; unsupported cases use the ordinary roof envelope. The broad-eave variant changes the roof profile within that footprint, not a projected overhang. Selection is a regional fallback, not observed building evidence.

Mapped material, facade colour, roof form, roof colour/imagery, height, floor count and footprint evidence retain priority. Neighbour material/roof consensus also precedes regional fallbacks. Low ordinary buildings receive regional material/roof defaults; taller and specialized structures keep their existing structural systems. Regional facade proportions/details are bounded to compatible ordinary buildings up to 12 floors. Churches, terminals, parking decks, industrial plant and other specialist geometry retain their purpose-specific renderers.

The mapped footprint, height and access planning remain authoritative; regional fallback roofs may change the silhouette within that envelope. This implementation does not invent courtyards, balconies, verandas, stilt heights, domes or sacred motifs from a regional name. Adobe, bamboo and thatch are not new asset families in this update. Rendered surfaces can suggest local colour but are not claimed to reproduce those construction systems.

## Performance, determinism and packaging

Geography uses a process-local spatial index and a bounded 8,192-entry exact-coordinate query cache. No network requests occur during regional selection. Profiles and polygon data participate in code/cache identity; both data identities are also included in context manifests. The source location is shared across near/far/sky planning, independent of render-frame rebasing.

Additional facade decoration is limited to 96 components per building, 24 per elevation and 16 window canopies. Wall details are clipped around openings; sash/screens remain in existing apertures. Existing mesh chunk limits, progressive publication and collision scheduling are unchanged.

`tools/prepare_regional_geography.py` rebuilds the polygon map from pinned upstream GeoJSON. `tools/compile_regional_profiles.py` validates the three image-reviewed authoring files and installs all 64 profiles. `tools/regional_theme_preview.py` renders actual generated meshes, records fingerprints and measures offline generation. The comparison sheets select representative local-detail variants using normal deterministic seeds; real buildings also receive ordinary/contemporary variants.

## Validation and limitations

All 64 example locations and an independent set of cities/islands/border cases are checked. Tests compile near/lite/collision meshes for each theme, check mapped-evidence precedence, worker serialization, detail budgets, source-frame stability, disabled-profile handling and cache inputs. Integrated building tests also cover roofs, garages, churches, terminals, facades, progressive chunks and sites.

The generated comparison sheets approximate material colours and omit the game lighting/texture pipeline. Offline measurements are not game FPS measurements. Native BeamNG appearance, streaming and driving acceptance are still required; no claim of worldwide visual ground truth is made. Each profile is grounded in a viewed locality photograph, with authored interpretation and scope notes below. A photograph does not establish the frequency of a style across an entire region.

## Image-reviewed design foundation

Three Terra subagents reviewed the photographic references and refined the parameters. Reference photographs are linked for attribution and inspection, not redistributed as game assets.

### 01. US Northeast

Stable ID: `us_northeast`. Routing example: Boston.

Stacked porches and aligned windows in older Boston triple-deckers; modern infill varies. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.05 m wide at 2.7 m bays; pitch prior 28–40 degrees; details: sash, lintels. Dimensions and weights are authored, not surveyed.

- [Boston triple deckers](https://bostonpreservation.org/news-item/short-history-bostons-triple-deckers) — [viewed photograph](https://bostonpreservation.org/sites/default/files/inline-images/Triple%20Deckers%20-%20Taft%20Street%20-%20Matthew%20Dickey_0.jpg). Gray and cream horizontal siding, white trim, tall aligned windows and stacked porches.

### 02. US Southeast and Gulf

Stable ID: `us_southeast`. Routing example: Charleston.

NPS photograph shows one historic Charleston cottage with horizontal timber siding, a gabled roof and a long porch. Contemporary Southeastern stock is diverse; this one cottage is not representative of the whole region. Parameters are authored interpretations, not survey measurements.

Implemented controls: windows 1.12 m wide at 2.9 m bays; pitch prior 22–35 degrees; details: sash, shutters. Dimensions and weights are authored, not surveyed.

- [Jackson Street Freedman’s Cottages](https://www.nps.gov/places/jackson-street-freedman-s-cottages.htm) — [viewed photograph](https://www.nps.gov/common/uploads/place/nri/20180306/places/D74914C7-1DD8-B71B-0BF8DCEA87D8D92A/D74914C7-1DD8-B71B-0BF8DCEA87D8D92A.jpg). Weathered horizontal timber siding, a gabled roof and a long shallow porch on one historic cottage.

### 03. US Midwest and Great Plains

Stable ID: `us_midwest`. Routing example: Chicago.

The Chicago Architecture Center image shows a row of brick bungalows with low shingle roofs and grouped windows. Modern Midwestern stock also includes simpler siding-clad homes and diverse regional forms. Dormers are not implemented. Parameters are authored interpretations, not survey measurements.

Implemented controls: windows 1.13 m wide at 2.9 m bays; pitch prior 23–36 degrees; details: lintels, sash. Dimensions and weights are authored, not surveyed.

- [Chicago Bungalow, Chicago Architecture Center](https://www.architecture.org/online-resources/buildings-of-chicago/chicago-bungalow) — [viewed photograph](https://cdn.builder.io/api/v1/image/assets%2Fe61abde79d954ddab2b6092044c4b5a1%2F9cf096355f80428eb10b0ed7ab947136). A row of brick bungalows, low pitched shingle roofs, grouped white framed windows and dormers.

### 04. US Southwest

Stable ID: `us_southwest`. Routing example: Tucson.

NPS image documents Barrio Libre in Tucson: the pictured theater and neighboring low frontage have rendered walls and parapets. It is a historic nonresidential example, not evidence of prevalence across the Southwest; modern suburban houses are also included. Adobe is not a supported material and render is an approximation. Parameters are authored interpretations.

Implemented controls: windows 1.2 m wide at 3.15 m bays; pitch prior 15–23 degrees; details: screens, canopies. Dimensions and weights are authored, not surveyed.

- [Barrio Libre, National Park Service](https://home.nps.gov/places/barrio-libre.htm) — [viewed photograph](https://home.nps.gov/common/uploads/cropped_image/primary/1DA72857-F50E-0C5B-4E48564C688E2219.jpg?mode=crop&quality=90&width=1600). Tucson streetscape with low, flush fronted rendered walls, a flat parapet and warm ochre and pale paint; the pictured main building is a theater, not a residence.

### 05. US Pacific Coast

Stable ID: `us_pacific`. Routing example: Portland.

Portland image shows low gabled painted houses with contrasting trim; modern stock includes simpler forms. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.15 m wide at 2.85 m bays; pitch prior 26–39 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Portland residential street](https://www.portland.gov/ppd/residential-permitting) — [viewed photograph](https://www.portland.gov/sites/default/files/styles/2_1_800w/public/2019-08/26887881281_f895dc1107_o.jpg?itok=cuwspzq6). Painted homes with contrasting trim and porches.

### 06. Atlantic Canada and Quebec

Stable ID: `canada_atlantic`. Routing example: Halifax.

Halifax street shows narrow painted siding fronts and white window trim; contemporary forms are simpler. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.0 m wide at 2.55 m bays; pitch prior 30–42 degrees; details: sash, lintels. Dimensions and weights are authored, not surveyed.

- [Moran Street Halifax](https://commons.wikimedia.org/wiki/File:Moran_Street_Halifax.jpg) — [viewed photograph](https://upload.wikimedia.org/wikipedia/commons/c/cc/Moran_Street_Halifax.jpg). Attached houses, painted facades and modest windows.

### 07. Canadian Prairies and interior

Stable ID: `canada_prairie`. Routing example: Winnipeg.

Winnipeg photograph shows modest detached pale houses with dark gabled roofs and small windows. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.25 m wide at 3.05 m bays; pitch prior 25–38 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Winnipeg homes](https://www.mtlblog.com/canada-house-prices-manitoba) — [viewed photograph](https://www.mtlblog.com/media-library/a-row-of-houses-in-winnipeg.jpg?coordinates=0%2C0%2C0%2C0&height=700&id=61466702&quality=85&width=1245). Detached houses with light siding and front steps.

### 08. Coastal British Columbia

Stable ID: `canada_pacific`. Routing example: Vancouver.

Vancouver street shows repeated gables, earth-toned cladding and light trim; contemporary infill varies. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.2 m wide at 3.0 m bays; pitch prior 25–38 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Vancouver suburban street](https://www.karmelalla.com/anastasia-in-canada) — [viewed photograph](https://www.karmelalla.com/assets/images/posts/stories/2017-12-14-anastasia-in-canada/14-1.jpg). Repeated gables, dark shingles, earth-toned siding and pale trim in a residential street.

### 09. Alaska, northern Canada and Greenland

Stable ID: `arctic_north_america`. Routing example: Iqaluit.

Iqaluit photograph shows recent low apartment blocks with vivid cladding and small regular windows; older stock differs. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.05 m wide at 2.6 m bays; pitch prior 20–32 degrees; details: screens. Dimensions and weights are authored, not surveyed.

- [Iqaluit multi-family housing](https://evoqarchitecture.com/en/projects/multi-family-housing-in-iqaluit) — [viewed photograph](https://evoqarchitecture.com/content/images/Projects/Multiplexes-%C3%A0-Iqaluit/04-EVOQ-Iqaluit-Multiplexes-Andrew-Latreille.jpg). Recent low apartment blocks with vivid red, orange, blue and gray panels and simple rectangular windows.

### 10. Mexico and northern Mesoamerica

Stable ID: `latin_american_local`. Routing example: Mexico City.

Mexico City photo shows attached flat-roofed two-storey fronts, barred windows and subdued render. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.12 m wide at 2.7 m bays; pitch prior 15–24 degrees; details: screens, canopies. Dimensions and weights are authored, not surveyed.

- [Ampliación Casas Alemán](https://propiedades.com/inmuebles/casa-en-venta-puerto-progreso-casas-aleman-07580-ciudad-de-mexico-cdmx-ampliacion-casas-aleman-df-30477311) — [viewed photograph](https://propiedadescom.s3.amazonaws.com/files/600x400/ccde1911-b10c-11f0-9607-d1a6f8e11200.png). Attached two-storey homes, barred windows and distinct painted fronts.

### 11. Caribbean and Atlantic island towns

Stable ID: `caribbean_creole`. Routing example: Havana.

Havana photograph shows low attached pink, yellow and blue painted houses and metal grilles; other islands differ. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.2 m wide at 2.8 m bays; pitch prior 16–26 degrees; details: shutters, screens. Dimensions and weights are authored, not surveyed.

- [Havana street](https://depositphotos.com/es/photos/downtown-kingston.html?offset=1300) — [viewed photograph](https://st2.depositphotos.com/3269785/47322/i/450/depositphotos_473222246-stock-photo-view-havana-cuba.jpg). Pastel fronts and window grilles; image metadata labels Havana.

### 12. Central American isthmus

Stable ID: `central_america`. Routing example: San José.

San José street shows low closely spaced houses, colorful fronts and varied roof profiles; contemporary concrete is included. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.15 m wide at 2.8 m bays; pitch prior 20–32 degrees; details: screens, canopies. Dimensions and weights are authored, not surveyed.

- [San José street](https://unsplash.com/es/s/fotos/costa-rica-san-jos%C3%A9) — [viewed photograph](https://images.unsplash.com/photo-1590268879033-e53b7bcc3338?auto=format&fit=crop&fm=jpg&ixlib=rb-4.1.0&q=60&w=3000). Closely spaced, differently painted houses along a residential street.

### 13. Andean highlands

Stable ID: `andean_highlands`. Routing example: Quito.

Quito image shows dense painted multilevel residential buildings and many flat roofs; coastal Peru and Ecuador are covered by modern rendered/concrete flat-roof variants. Distant view limits detail. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.08 m wide at 2.7 m bays; pitch prior 18–30 degrees; details: screens, lintels. Dimensions and weights are authored, not surveyed.

- [Quito San Roque](https://www.novo-monde.com/en/things-to-do-quito-ecuador/) — [viewed photograph](https://www.novo-monde.com/app/uploads/2023/10/san-roque-quito-1024x806.jpg). Densely packed multilevel painted hillside houses; distant view.

### 14. Coastal and southeastern Brazil

Stable ID: `brazil_coastal`. Routing example: Recife.

Recife street shows low painted fronts, green shutters and simple roof edge; contemporary masonry varies. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.22 m wide at 2.95 m bays; pitch prior 18–29 degrees; details: screens, canopies. Dimensions and weights are authored, not surveyed.

- [Barro Recife](https://www.expoimovel.com/imovel/casas-alugar-locacao-barro-recife-pernambuco/413609/pt/BR) — [viewed photograph](https://img.expoimovel.com/imagens_classificados/383/413609_383_CA0062_02.jpg). Small painted houses on a residential street.

### 15. Amazon and Guianas

Stable ID: `amazon_guianas`. Routing example: Georgetown.

Georgetown photograph shows a weathered timber gabled dwelling and shuttered openings; modern masonry is also included. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.08 m wide at 2.75 m bays; pitch prior 23–34 degrees; details: shutters, screens. Dimensions and weights are authored, not surveyed.

- [Georgetown wooden dwelling](https://myadventuresacrosstheworld.com/georgetown-guyana/) — [viewed photograph](https://myadventuresacrosstheworld.com/wp-content/uploads/2018/10/Georgetown-Guyana-e1540661080255.jpg). Weathered timber dwelling with gable, small porch and shuttered openings.

### 16. Southern Cone plains and Patagonia

Stable ID: `southern_cone`. Routing example: Buenos Aires.

Buenos Aires housing image shows two-storey red brick and pale walls with shallow red tiled gables; modern urban blocks vary. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.3 m wide at 3.05 m bays; pitch prior 20–32 degrees; details: screens, lintels. Dimensions and weights are authored, not surveyed.

- [Comuna 12 houses](https://www.nueva-ciudad.com.ar/notas/202308/52007-presentaran-el-proyecto-para-restituir-el-nombre-del-barrio-presidente-juan-domingo-peron-de-la-comuna-12.html) — [viewed photograph](https://www.nueva-ciudad.com.ar/advf/imagenes/editadas/64ca52415fe65_800x488.jpg). Two-storey houses with tile roofs, masonry and small gardens.

### 17. Chilean Pacific settlements

Stable ID: `chile_pacific`. Routing example: Valparaíso.

Valparaíso distant hillside image shows closely packed painted homes and many simple gabled roofs; details are too distant to measure. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.12 m wide at 2.75 m bays; pitch prior 22–35 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Valparaíso hillside](https://www.undp.org/es/chile/noticias/indice-de-desarrollo-humano-2022-chile-mantiene-primer-lugar-en-la-region-con-desafios-persistentes-en-reduccion-de-desigualdades) — [viewed photograph](https://www.undp.org/sites/g/files/zskgke326/files/2022-09/Valpara%C3%ADso%202022.jpg). Dense multicoloured hillside housing, seen from a distance.

### 18. Britain, Ireland and Atlantic islands

Stable ID: `eu_atlantic`. Routing example: London.

Buff brick terraces, white lintels and tall sash windows; this older London street is one local variant. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.18 m wide at 2.75 m bays; pitch prior 18–30 degrees; details: sash, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Tripadvisor: Over a billion reviews & contributions for Hotels, Attractions, Restaurants, and more](https://www.holidaylettings.co.uk/rentals/london/14597288) — [viewed photograph](https://photos.holidaylettings.co.uk/media/vr-splice-j/0f/93/12/03.jpg#). Buff brick terraces, white lintels and tall sash windows; this older London street is one local variant.

### 19. Iberian Mediterranean and interior

Stable ID: `eu_mediterranean`. Routing example: Lisbon.

Lisbon street has pastel rendered fronts, tall narrow windows and light trim; contemporary blocks need separate local samples. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.05 m wide at 2.6 m bays; pitch prior 21–33 degrees; details: shutters, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Lisbon Living Alcântara – Modern 2BR Flat - Distrito de Lisboa | Vrbo](https://www.vrbo.com/11845448ha) — [viewed photograph](https://media.vrbo.com/lodging/117000000/116080000/116073400/116073369/a32636cb.jpg?impolicy=resizecrop&ra=fill&rh=575&rw=575#). Lisbon street has pastel rendered fronts, tall narrow windows and light trim; contemporary blocks need separate local samples.

### 20. Nordic countries and North Atlantic

Stable ID: `nordic_cold`. Routing example: Bergen.

Bergen wooden street has pale horizontal boards, white multi-pane frames and pitched roofs; modern apartments also appear behind. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.15 m wide at 2.55 m bays; pitch prior 30–43 degrees; details: sash, lintels, timber_bands. Dimensions and weights are authored, not surveyed.

- [Bergen twilight streets](https://www.getyourguide.com/tr-tr/bergen-l1132/bergen-in-alacakaranlik-buyusu-bir-aksam-macerasi-t676492/) — [viewed photograph](https://cdn.getyourguide.com/image/format%3Dauto%2Cfit%3Dcrop%2Cgravity%3Dauto%2Cquality%3D60%2Cwidth%3D450%2Cheight%3D450%2Cdpr%3D2/tour_img/0339d3fc35dbfb8d865a532a6fd20b1a79802939e2bca58ba20ced350261b336.jpg). Bergen wooden street has pale horizontal boards, white multi-pane frames and pitched roofs; modern apartments also appear behind.

### 21. France and regional traditions

Stable ID: `france_regional`. Routing example: Lyon.

Lyon-area low houses show warm render, red shutters and low red pitched roofs; dense contemporary housing varies. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.08 m wide at 2.7 m bays; pitch prior 27–39 degrees; details: shutters, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Plateforme de participation citoyenne de la Métropole de Lyon - Bâtis des Castors Lyon 5 en Patrimoine d'Intérêt Patrimonial (PIP)](https://jeparticipe.grandlyon.com/project/test-concertation-pluh/collect/test-depot-etape-de-depot-titre-de-la-page/proposals/batis-des-castors-lyon-5-en-patrimoine-dinteret-patrimonial-pip) — [viewed photograph](https://jeparticipe.grandlyon.com/cdn-cgi/image/width%3D2560%2Cformat%3Dauto/https%3A/jeparticipe.grandlyon.com/media/default/0001/01/a4530c0a1cee2739e0ffbcedf529c8f733f81fc5.jpeg#). Lyon-area low houses show warm render, red shutters and low red pitched roofs; dense contemporary housing varies.

### 22. Low Countries

Stable ID: `low_countries`. Routing example: Amsterdam.

Amsterdam brick row fronts have white framed broad windows and repeated vertical bays; newer estates vary. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.42 m wide at 2.8 m bays; pitch prior 30–42 degrees; details: sash, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Appartement verkocht: Van Hogendorpstraat 131-1 1051 BM Amsterdam | Funda](https://www.funda.nl/detail/koop/verkocht/amsterdam/appartement-van-hogendorpstraat-131-1/43961744/) — [viewed photograph](https://cloud.funda.nl/valentina_media/207/707/990_1440x960.jpg#). Amsterdam brick row fronts have white framed broad windows and repeated vertical bays; newer estates vary.

### 23. German-speaking and central Europe

Stable ID: `central_europe`. Routing example: Berlin.

Berlin apartment block has restrained white render, small repeated windows and brick base with dark tiled roof. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.12 m wide at 2.85 m bays; pitch prior 18–30 degrees; details: lintels, floor_bands, canopies. Dimensions and weights are authored, not surveyed.

- [H&S Bau Berlin residential block](https://www.hsbauberlin.com/referenzen/architekten-u-planungsleistungen/) — [viewed photograph](https://image.jimcdn.com/app/cms/image/transf/dimension%3D2048x2048%3Aformat%3Djpg/path/s7aa3fe03c524ee43/image/i395637246100ec6b/version/1682507858/image.jpg). Berlin apartment block has restrained white render, small repeated windows and brick base with dark tiled roof.

### 24. Alpine settlements

Stable ID: `alpine`. Routing example: Chur.

Chur street shows yellow and cream plaster, colored shutters and framed vertical windows; avoid treating this street as all Alpine housing. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.05 m wide at 2.5 m bays; pitch prior 21–33 degrees; details: shutters, lintels, timber_bands. Dimensions and weights are authored, not surveyed.

- [Apartment to buy in Kasernenquartier (Chur)](https://www.homegate.ch/buy/apartment/district-kasernenquartier-chur/matching-list) — [viewed photograph](https://media2.homegate.ch/listings/v2/z261/4002689153/image/abf8a29c9610dea3c996868798b9c5d8.jpg#). Chur street shows yellow and cream plaster, colored shutters and framed vertical windows; avoid treating this street as all Alpine housing.

### 25. Italian peninsula and islands

Stable ID: `italy_regional`. Routing example: Bologna.

Bologna row has warm red, ochre and cream rendered walls with shutters; arcades in photo are not generated. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.05 m wide at 2.65 m bays; pitch prior 24–36 degrees; details: shutters, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Bologna]() — [viewed photograph](https://q-xx.bstatic.com/xdata/images/hotel/max1024x768/115000773.jpg?k=d3183b476e3dbba7e44e5145ad8298aaf9361cbc63dc22774b5b7ef2295a6c2b&o=#). Bologna row has warm red, ochre and cream rendered walls with shutters; arcades in photo are not generated.

### 26. Adriatic and Balkan interior

Stable ID: `adriatic_balkans`. Routing example: Zagreb.

Zagreb street shows simple pale gabled houses and red tiled roofs; the visible balcony is not reproduced. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.16 m wide at 2.9 m bays; pitch prior 27–39 degrees; details: shutters, lintels, canopies. Dimensions and weights are authored, not surveyed.

- [Naselje Istrana i invalida | Arhitektura Zagreba](https://www.arhitektura-zagreba.com/zgrade/moscenicka-2) — [viewed photograph](https://storage.googleapis.com/arhitektura-zagr-1514718358225.appspot.com/photos/Veprina%C4%8Dka__22.JPG#). Zagreb street shows simple pale gabled houses and red tiled roofs; the visible balcony is not reproduced.

### 27. Greece and Cyprus

Stable ID: `aegean`. Routing example: Athens.

Athens older street shows yellow and pink render, shutters, vertical windows and tile roof edges; modern apartment stock differs. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.08 m wide at 2.6 m bays; pitch prior 30–42 degrees; details: shutters, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [The New Geography Of Overtourism: How Cruises and Short-Term Rentals Are Reshaping Destinations | Outlook Traveller](https://www.outlooktraveller.com/News/the-new-geography-of-overtourism-how-cruises-and-short-term-rentals-are-reshaping-destinations) — [viewed photograph](https://media.assettype.com/outlooktraveller/2024-09-10/kgj1p37y/shutterstock_2227631575.jpg?auto=format%2Ccompress&dpr=1.0&fit=max&format=webp&w=801#). Athens older street shows yellow and pink render, shutters, vertical windows and tile roof edges; modern apartment stock differs.

### 28. Eastern Europe and Baltic

Stable ID: `eastern_europe`. Routing example: Riga.

Riga residential lane has pale vertical siding, steep dark gable and small windows; panel estates are another common stock type. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.02 m wide at 2.5 m bays; pitch prior 30–43 degrees; details: sash, lintels, timber_bands. Dimensions and weights are authored, not surveyed.

- [Category:Enkura iela (Riga) - Wikimedia Commons](https://commons.wikimedia.org/wiki/Category%3AEnkura_iela_%28Riga%29) — [viewed photograph](https://upload.wikimedia.org/wikipedia/commons/thumb/5/5f/Enkura_iela_%284%29.jpg/1280px-Enkura_iela_%284%29.jpg#). Riga residential lane has pale vertical siding, steep dark gable and small windows; panel estates are another common stock type.

### 29. Russia and northern Eurasia

Stable ID: `russia_north`. Routing example: Moscow.

Street photo shows older multistorey fronts with aligned windows and horizontal moldings; modern panel apartments differ. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.15 m wide at 2.75 m bays; pitch prior 21–33 degrees; details: sash, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Доходный дом москва: фото, изображения и картинки](https://picsy.ru/photo/dokhodnyj-dom-moskva-39505739) — [viewed photograph](https://avatars.mds.yandex.net/get-pdb/236760/bbbb9e74-9e0a-4a48-a55a-dc88cdbdef53/s1200#). Street photo shows older multistorey fronts with aligned windows and horizontal moldings; modern panel apartments differ.

### 30. West African Atlantic and Gulf of Guinea

Stable ID: `african_local`. Routing example: Accra.

Accra planned estate shows low cream homes, pale blue metal roofs and dark framed rectangular windows; not representative of all stock. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.2 m wide at 3.1 m bays; pitch prior 24–36 degrees; details: screens, canopies, lintels. Dimensions and weights are authored, not surveyed.

- [Real Estate For Sale Accra Ghana at Katie Felton blog](https://storage.googleapis.com/dzhansegjorroe/real-estate-for-sale-accra-ghana.html) — [viewed photograph](https://www.ghanarealestatedevelopers.com/wp-content/uploads/2017/02/3-Bedrooms-UT-properties-For-sale-in-Accra1-1.jpg#). Accra planned estate shows low cream homes, pale blue metal roofs and dark framed rectangular windows; not representative of all stock.

### 31. Maghreb and northwest Africa

Stable ID: `maghreb`. Routing example: Casablanca.

Casablanca lane has pale flat-fronted buildings, small windows and painted warm accents; retain contemporary plain facade variants. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.12 m wide at 2.8 m bays; pitch prior 27–39 degrees; details: shutters, screens, floor_bands. Dimensions and weights are authored, not surveyed.

- [Learning from Casablanca | aamatters](https://www.aamatters.nl/learning-from-casablanca) — [viewed photograph](https://static.wixstatic.com/media/e11c5e_cd474d07c0964bdf8630a77da6041191~mv2.jpg/v1/fill/w_557%2Ch_543%2Cal_c%2Cq_80%2Cenc_avif%2Cquality_auto/e11c5e_cd474d07c0964bdf8630a77da6041191~mv2.jpg#). Casablanca lane has pale flat-fronted buildings, small windows and painted warm accents; retain contemporary plain facade variants.

### 32. Sahel and western Sudanian belt

Stable ID: `sahel`. Routing example: Bamako.

Bamako image shows contemporary boxy cream and charcoal house with compact square openings; earthen traditions are not represented by render. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.02 m wide at 2.95 m bays; pitch prior 30–42 degrees; details: screens, lintels, canopies. Dimensions and weights are authored, not surveyed.

- [Bamako Villas and Beach house | Best Price on cozycozy](https://www.cozycozy.com/us/bamako-villa-rentals) — [viewed photograph](https://q-xx.bstatic.com/xdata/images/hotel/max1440/643703268.jpg?a=1311119&k=5a7509eef2341afc29dc383bb183946cc7e7fe2d22bcc9461d73ae31382f7a4f&o=#). Bamako image shows contemporary boxy cream and charcoal house with compact square openings; earthen traditions are not represented by render.

### 33. Nile Valley and northeast desert

Stable ID: `nile_valley`. Routing example: Cairo.

Cairo-area image shows sand-coloured multi-storey residential blocks with horizontal bands and recessed openings. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.12 m wide at 3.0 m bays; pitch prior 18–30 degrees; details: screens, floor_bands, lintels. Dimensions and weights are authored, not surveyed.

- [Las 16 mejores Villas en El Cairo, Egipto – villastogo.com](https://elcairo.villastogo.com/es/) — [viewed photograph](https://elcairo.villastogo.com/img-wp/images/700x500w/14306/1430619/1430619091.JPEG#). Cairo-area image shows sand-coloured multi-storey residential blocks with horizontal bands and recessed openings.

### 34. Horn of Africa and Ethiopian highlands

Stable ID: `horn_africa`. Routing example: Addis Ababa.

Addis Ababa street has grey masonry-like walls, dark windows and red pitched roofs; locality and building type vary. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.1 m wide at 2.95 m bays; pitch prior 21–33 degrees; details: lintels, floor_bands, canopies. Dimensions and weights are authored, not surveyed.

- [Houses for Rent in Addis Ababa, Ethiopia | 2-4 Bedroom & Furnished Homes](https://livingethio.com/site/property/house-for-rent) — [viewed photograph](https://d2r4axsrvib8z2.cloudfront.net/1783415142010_7brjwz6ed1m_1783415056473_py4ka9oh3wm_photo_20260707_104002Copy.webp#). Addis Ababa street has grey masonry-like walls, dark windows and red pitched roofs; locality and building type vary.

### 35. Swahili coast and East African interior

Stable ID: `swahili_east_africa`. Routing example: Dar es Salaam.

Dar es Salaam lane shows pale walls and a grey corrugated pitched metal roof, with dark gate; photo reveals limited facade detail. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.15 m wide at 3.0 m bays; pitch prior 24–36 degrees; details: screens, canopies, lintels. Dimensions and weights are authored, not surveyed.

- [Nyumba Inauzwa Dar es salaam | Kupatana](https://kupatana.com/tz/listings/p/nyumba-inauzwa-dar-es-salaam/629623fbbc5d2c000121d48f294648) — [viewed photograph](https://kupatana.com/api/v1/filestorage/image/large/9ecd6819e24e383b50b17de6492bf587.jpg#). Dar es Salaam lane shows pale walls and a grey corrugated pitched metal roof, with dark gate; photo reveals limited facade detail.

### 36. Central African forest and plateau

Stable ID: `central_africa`. Routing example: Yaounde.

Yaounde photograph shows light green and cream painted house with dark hipped roof; arched balcony is not implemented. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.12 m wide at 3.05 m bays; pitch prior 27–39 degrees; details: screens, lintels, canopies. Dimensions and weights are authored, not surveyed.

- [Yaounde]() — [viewed photograph](https://q-xx.bstatic.com/xdata/images/hotel/max1024x768/585868787.jpg?ar=16x9&k=1623ede594fdac6ec4249522462602df62f9397ae19ec35588ca61632db97ac9&o=%3Fs%3D375x210#). Yaounde photograph shows light green and cream painted house with dark hipped roof; arched balcony is not implemented.

### 37. Southern African plateau and coasts

Stable ID: `southern_africa`. Routing example: Johannesburg.

Johannesburg suburban example has pale walls, red hipped roof and broad dark frames behind boundary wall. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 1.35 m wide at 3.15 m bays; pitch prior 30–42 degrees; details: lintels, canopies, screens. Dimensions and weights are authored, not surveyed.

- [Orange Grove, Johannesburg Property : Property and houses for sale in Orange Grove, Johannesburg : Property24.com](https://www.property24.com/for-sale/orange-grove/johannesburg/gauteng/4365) — [viewed photograph](https://images.prop24.com/363267744#). Johannesburg suburban example has pale walls, red hipped roof and broad dark frames behind boundary wall.

### 38. Madagascar and western Indian Ocean

Stable ID: `indian_ocean_africa`. Routing example: Antananarivo.

Madagascar image shows red-orange masonry gables and steep dark roofs; thatch in photo is unsupported, and urban stock differs. Values and weights are artistic interpretations, not survey data.

Implemented controls: windows 0.95 m wide at 2.65 m bays; pitch prior 30–43 degrees; details: shutters, lintels, timber_bands. Dimensions and weights are authored, not surveyed.

- [Antananarivo : Custom Walking Tour With A Guide (Private Tour) in Antananarivo | Pelago](https://www.pelago.com/en-GB/activity/p5fhdu2f0-private-custom-walking-tour-with-a-local-guide-in-antananarivo-antananarivo/) — [viewed photograph](https://www.pelago.com/img/products/MG-Madagascar/private-custom-walking-tour-with-a-local-guide-in-antananarivo/5b579d43-4dc9-4ea6-9813-d2f3689c27e3_private-custom-walking-tour-with-a-local-guide-in-antananarivo.jpg#). Madagascar image shows red-orange masonry gables and steep dark roofs; thatch in photo is unsupported, and urban stock differs.

### 39. Arabian Peninsula and Gulf

Stable ID: `arid_warm`. Routing example: Muscat.

Light stucco villas with gated openings; this upscale street is one sample, not all Gulf housing. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.12 m wide at 2.9 m bays; pitch prior 18–30 degrees; details: screens, canopies, floor_bands. Dimensions and weights are authored, not surveyed.

- [Muscat residential street](https://om.opensooq.com/en/muscat/amerat/property/lands-for-sale) — [viewed photograph](https://opensooq-images.os-cdn.com/previews/2048x0/1d/6a/1d6adfdb2d800d02cc7c115bd754ad457c17fea18cb07f6a2839182fb8fc205d.jpg.webp). Cream and white modern houses with flat rooflines and recessed windows.

### 40. Levant and eastern Mediterranean

Stable ID: `levant`. Routing example: Amman.

Amman stone residential frontage and rectangular openings; the photographed modernist villa is a single example. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.25 m wide at 3.1 m bays; pitch prior 18–31 degrees; details: lintels, floor_bands, canopies. Dimensions and weights are authored, not surveyed.

- [Amman Azar House](https://www.csbe.org/new-gallery) — [viewed photograph](https://images.squarespace-cdn.com/content/v1/5671433fc647ad9f55531f40/1563106528644-1LJXK0R55LHJIM6XYGB4/Azar%2BHouse%2B2.jpg?format=2500w). Light stone wall and pale flat-roofed house with rectangular openings.

### 41. Anatolia and Caucasus

Stable ID: `anatolia_caucasus`. Routing example: Tbilisi.

Pale rendered Tbilisi residential block with white trim; balconies are not modelled. Contemporary infill varies. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.2 m wide at 2.85 m bays; pitch prior 22–37 degrees; details: sash, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Tbilisi residential block](https://www.airbnb.com.tr/rooms/1097823535379756405) — [viewed photograph](https://a0.muscache.com/im/pictures/hosting/Hosting-1097823535379756405/original/70e78b45-1df4-4456-9229-7eaf3b36411e.jpeg?im_w=720). Pale peach street facade, tall white-trimmed windows and horizontal bands.

### 42. Iranian plateau and Afghan uplands

Stable ID: `iran_plateau`. Routing example: Tehran.

Low-rise brick apartments with grilles in Tehran; desert earthen fabric and later apartment stock differ. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.16 m wide at 2.8 m bays; pitch prior 17–28 degrees; details: screens, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Tehran low-rise residential district](https://caoi.ir/fa/study/976) — [viewed photograph](https://www.caoi.ir/images/1-Bulletins/Study/koie_maskoni/shahrara-tehran.jpg). Brown brick apartments with small rectangular windows and metal security grilles.

### 43. Mesopotamian plains

Stable ID: `mesopotamia`. Routing example: Baghdad.

Baghdad street shows simple concrete houses and gates; flat roofs are an artistic candidate, not a census. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.04 m wide at 2.75 m bays; pitch prior 16–27 degrees; details: screens, canopies, lintels. Dimensions and weights are authored, not surveyed.

- [Baghdad residential street](https://964media.com/278245/) — [viewed photograph](https://cdn.964media.com/bfefbcb7-e5d2-4b75-3836-dd16bd700b00/full169). Plain grey-beige walls, flat rooflines and metal gates along a residential road.

### 44. Central Asian oasis towns

Stable ID: `central_asia_oases`. Routing example: Samarkand.

Mahalla alley shows simple painted and brick street walls; modern apartments also occur locally. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.04 m wide at 2.65 m bays; pitch prior 20–34 degrees; details: lintels, screens, canopies. Dimensions and weights are authored, not surveyed.

- [Samarkand mahalla alley](https://www.sekainoasameshi.com/entry/2024/02/27/233629) — [viewed photograph](https://cdn-ak.f.st-hatena.com/images/fotolife/d/daigo520/20240227/20240227232157.jpg). Tan brick and salmon plaster facades, dark windows and visible sloping eaves.

### 45. Central Asian steppe and mountain towns

Stable ID: `central_asia_steppe`. Routing example: Almaty.

Almaty cottage development has pitched coloured roofs; planned premium housing is only one local stock type. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.3 m wide at 3.15 m bays; pitch prior 25–42 degrees; details: sash, lintels, canopies. Dimensions and weights are authored, not surveyed.

- [Almaty cottage street](https://krisha.kz/complex/show/dostyk-kg/) — [viewed photograph](https://krisha-photos.kcdn.online/content/45/793357e4cd42ca702_20160716_155631-dostyk-kg-750x470.jpg). Red and tan houses with pitched red roofs and light window trim.

### 46. Indus, Gangetic plains and western India

Stable ID: `indus_gangetic`. Routing example: Ahmedabad.

Cream two-storey Hansol houses with gates; historic pol timber detail is a separate local variant. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.15 m wide at 2.85 m bays; pitch prior 16–29 degrees; details: screens, canopies, floor_bands. Dimensions and weights are authored, not surveyed.

- [Ahmedabad Hansol street](https://www.realestateindia.com/property-detail/3bkh-individual-houses-villas-for-rent-in-hansol-ahmedabad-220-sq-yards-17-000-1204887.htm) — [viewed photograph](https://dynamic.realestateindia.com/prop_images/1918381/1204887_5.jpg). Cream row houses with white horizontal bands and shallow window awnings.

### 47. Peninsular India and Deccan

Stable ID: `india_peninsular`. Routing example: Bengaluru.

Pastel two- and three-storey housing and gates in Bengaluru; roof choices remain locality-dependent. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.2 m wide at 2.9 m bays; pitch prior 19–34 degrees; details: screens, canopies, floor_bands. Dimensions and weights are authored, not surveyed.

- [Bengaluru residential lane](https://www.magicbricks.com/Tata-Silk-Farm-in-Bangalore-Overview) — [viewed photograph](https://img.staticmb.com/mbphoto/locality/cropped_images/2024/Dec/5/Photo_h470_w1080/103039_IMG-20241003-WA0080---Hassan-Ansari_470_1080.jpg). Pale yellow, blue-green and peach houses with rectangular openings and shallow window hoods.

### 48. Bengal and northeast South Asia

Stable ID: `bengal_delta`. Routing example: Dhaka.

Pallabi apartment facades show grilles and muted paint; riverside rural housing differs from this urban sample. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.25 m wide at 2.95 m bays; pitch prior 17–30 degrees; details: screens, floor_bands, canopies. Dimensions and weights are authored, not surveyed.

- [Dhaka Pallabi street](https://www.airbnb.co.in/rooms/1190132335599765987) — [viewed photograph](https://a0.muscache.com/im/pictures/miso/Hosting-1190132335599765987/original/17f7eea3-7757-49e0-95cf-6eb199a50342.jpeg?im_w=720). Blue-grey apartment facade with orange panels, small rectangular windows and window grilles.

### 49. Himalayan foothills and valleys

Stable ID: `himalayan`. Routing example: Kathmandu.

Historic Kathmandu street shows narrow vertical painted windows; contemporary housing varies. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.02 m wide at 2.55 m bays; pitch prior 24–39 degrees; details: timber_bands, lintels, screens. Dimensions and weights are authored, not surveyed.

- [Kathmandu painted houses](https://raingod.com/photos/asia/nepal/kathmandu/painted-houses/) — [viewed photograph](https://raingod.com/photos/asia/nepal/kathmandu/photos/kathmandu-016-720.jpg). Closely packed painted houses with narrow vertical teal-trimmed windows and red decorative panels.

### 50. Sri Lanka and Maldives

Stable ID: `sri_lanka_maldives`. Routing example: Colombo.

Cream Colombo villas have grilles and shaded entries; the affluent lane is not representative of all island housing. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.3 m wide at 3.1 m bays; pitch prior 22–36 degrees; details: screens, canopies, shutters. Dimensions and weights are authored, not surveyed.

- [Colombo Flower Road lane](https://flower-road-apartment.colombohotels.net/en/) — [viewed photograph](https://flower-road-apartment.colombohotels.net/data/Pics/OriginalPhoto/3533/353362/353362162/flower-road-villa-colombo-pic-41.JPEG). White and cream houses, dark window grilles and a visible pitched eave.

### 51. Japan and Ryukyu islands

Stable ID: `jp_temperate`. Routing example: Tokyo.

Compact Tokyo houses show light walls and shuttered openings; historic machiya is a distinct variant. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.25 m wide at 2.8 m bays; pitch prior 23–38 degrees; details: shutters, screens, canopies. Dimensions and weights are authored, not surveyed.

- [Tokyo Nerima residential street](https://sumikae.ttfuhan.co.jp/tochi/YAAA14295/) — [viewed photograph](https://sumikae.ttfuhan.co.jp/sale_images/yuraku/0257000AAA14295-3.jpg). Light textured walls, horizontal roller shutters and visible tiled pitched roofs.

### 52. Northern and inland China

Stable ID: `china_north`. Routing example: Beijing.

Grey brick hutong houses and tile roofs are historic local fabric; modern apartment blocks require separate treatment. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.05 m wide at 2.65 m bays; pitch prior 22–36 degrees; details: screens, lintels, canopies. Dimensions and weights are authored, not surveyed.

- [Beijing hutong](https://www.visitbeijing.com.cn/article/4I0bcCJkPjP) — [viewed photograph](https://img-rs.huanqiucdn.cn/dp/api/files/imageDir/48c9503c5292ce6a7862fe4b6412015b.png). Grey brick walls and dark shallow tiled eaves along a narrow lane.

### 53. Southern China, Taiwan and coastal cities

Stable ID: `china_south`. Routing example: Taipei.

Taipei older apartment street has weathered facades and window grilles; shophouses and new towers are separate local types. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.35 m wide at 3.15 m bays; pitch prior 18–31 degrees; details: screens, canopies, floor_bands. Dimensions and weights are authored, not surveyed.

- [Taipei Jingxing Road](https://news.housefun.com.tw/photo/16679171407) — [viewed photograph](https://p1-news.hfcdn.com/p1-news/NzEwMjYybmV3cw%2C%2C/89f53be35247e8e9.jpg/qs/w%3D640). Weathered grey apartment facades with red panels and metal window cages.

### 54. Korean peninsula

Stable ID: `korea`. Routing example: Seoul.

Seoul low-rise brick villas and small apartments; hanok and high-rise housing require distinct selection. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.24 m wide at 2.85 m bays; pitch prior 20–35 degrees; details: sash, lintels, floor_bands. Dimensions and weights are authored, not surveyed.

- [Seoul residential alley](https://cm.asiae.co.kr/ranking-view/20240104/2024010316414106992) — [viewed photograph](https://cphoto.asiae.co.kr/listimglink/6/2024010409174418237_1704327464.jpg). Red brick low-rise facades and light framed windows in a narrow alley.

### 55. Tibetan plateau and high mountain settlements

Stable ID: `tibetan_plateau`. Routing example: Lhasa.

Historic Lhasa houses show white walls and dark window frames; this is not evidence of contemporary frequency. Render is only a visual proxy for earth. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 0.9 m wide at 2.45 m bays; pitch prior 16–27 degrees; details: timber_bands, screens, lintels. Dimensions and weights are authored, not surveyed.

- [Lhasa residential quarter](https://www.pbase.com/bmcmorrow/lhasamuslimqtr) — [viewed photograph](https://a4.pbase.com/o2/93/329493/1/105550111.Jo2x9iTa.TibetOct08399.jpg). White walls, dark window surrounds and a richly painted timber gallery in a historic alley.

### 56. Malay Peninsula and equatorial trading towns

Stable ID: `tropical_humid`. Routing example: Singapore.

Singapore shophouses have narrow fronts and awnings; conserved rows are distinct from contemporary apartments. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.18 m wide at 2.65 m bays; pitch prior 23–38 degrees; details: shutters, screens, canopies. Dimensions and weights are authored, not surveyed.

- [Singapore neighbourhood shophouses](https://www.edb.gov.sg/en/business-insights/insights/moving-to-singapore-which-neighbourhood-is-for-you.html) — [viewed photograph](https://www.edb.gov.sg/content/dam/edb-en/business-insights/insights/moving-to-singapore-which-neighbourhood-is-for-you/moving-to-singapore-which-neighbourhood-is-for-you-content11.jpg). White and brick low-rise frontages with horizontal windows and red awnings.

### 57. Mainland Southeast Asia

Stable ID: `mainland_southeast_asia`. Routing example: Hanoi.

Narrow Hanoi alley townhouses have muted paint and metal gates; stilt homes elsewhere are a separate type. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.2 m wide at 2.55 m bays; pitch prior 20–33 degrees; details: screens, canopies, floor_bands. Dimensions and weights are authored, not surveyed.

- [Hanoi alley houses](https://kinhtedothi.vn/sot-gia-nha-o-rieng-le-trong-ngo-tai-ha-noi.html) — [viewed photograph](https://resource.kinhtedothi.vn/2025/03/17/phan-khuc-nha-rieng-trong-ngo-dang-lien-tuc-tang-gia-thoi-gian-qua-anh-le-tam.jpg). Yellow and cream narrow frontages, dark gates and horizontal facade bands.

### 58. Indonesia and Timor

Stable ID: `indonesian_archipelago`. Routing example: Yogyakarta.

Kauman alley combines modest painted walls and shutters; present-day masonry differs by island. Thatch and bamboo assets are absent. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.08 m wide at 2.6 m bays; pitch prior 25–40 degrees; details: shutters, screens, canopies. Dimensions and weights are authored, not surveyed.

- [Yogyakarta Kauman alley](https://www.suaramuhammadiyah.id/read/masa-kecil-di-kauman) — [viewed photograph](https://cdn.suaramuhammadiyah.id/posts/image/Kauman-20240419145133.JPG). White walls, deep green shutters and doors, tiled pitched roofs and shallow eaves.

### 59. Philippine archipelago

Stable ID: `philippines`. Routing example: Manila.

Manila lane has concrete houses and barred windows; historic timber houses are distinct and bamboo/thatch assets are absent. Parameters are authored interpretations, not measured survey data.

Implemented controls: windows 1.25 m wide at 2.9 m bays; pitch prior 22–37 degrees; details: screens, canopies, shutters. Dimensions and weights are authored, not surveyed.

- [Manila residential lane](https://nextflight.ru/blog/philipines/manila/manila_zamanila) — [viewed photograph](https://nextflight.ru/upload/images/philippines/manila/IMG_9086.JPG). Grey and white flat-fronted houses with barred windows and shaded entries.

### 60. New Zealand and temperate southern Pacific

Stable ID: `nz_temperate`. Routing example: Wellington.

Wellington image shows older timber houses with decorative trim and tall windows; later suburban housing is simpler. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.15 m wide at 2.8 m bays; pitch prior 25–38 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Lipman Street Wellington](https://www.rnz.co.nz/news/national/324461/students-struggle-as-rents-rise-while-allowances-stay-put) — [viewed photograph](https://media.rnztools.nz/rnz/image/upload/s--g-F8PaMe--/c_scale%2Cf_auto%2Cq_auto%2Cw_1050/v1643301393/4OP57NW_image_crop_18271?_a=BACCd2AD). Timber houses with trim and bay windows; older stock.

### 61. Southeastern and temperate Australia

Stable ID: `au_southeast`. Routing example: Melbourne.

Melbourne street shows low brown brick houses with hipped tile roofs; rendered and contemporary forms are included. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.3 m wide at 3.1 m bays; pitch prior 20–32 degrees; details: sash, canopies. Dimensions and weights are authored, not surveyed.

- [Reservoir Melbourne](https://www.domain.com.au/news/properties-in-melbournes-inner-city-outer-fringe-risk-lower-valuations-than-buyers-paid-829482/) — [viewed photograph](https://res.akamaized.net/domain/image/upload/t_web/c_fill%2Cw_800%2Ch_450/v1539661073/Domain_Neighbourhoods_Reservoir-47_zz3e4p.jpg). Single-storey brick homes with tiled roofs.

### 62. Northern and inland Australia

Stable ID: `au_tropical_arid`. Routing example: Darwin.

Darwin example shows a light elevated house with broad shaded openings; inland arid housing also uses rendered masonry. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.35 m wide at 3.2 m bays; pitch prior 18–30 degrees; details: screens, canopies. Dimensions and weights are authored, not surveyed.

- [Parap Darwin house](https://www.realestate.com.au/sold/property-house-nt-parap-140476819) — [viewed photograph](https://i2.au.reastatic.net/800x600/28263cedacb1db0f2fb6cf953133e615aed12904e64588ce4636c2189f8f84b5/image.jpg). Elevated home with louvred windows and pale exterior; one tropical example.

### 63. Melanesia, Micronesia and Polynesia

Stable ID: `pacific_islands`. Routing example: Suva.

Suva estate photo shows two-storey pale blocks, broad openings and low-pitched roofs; islands and newer housing vary. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.25 m wide at 3.05 m bays; pitch prior 21–33 degrees; details: screens, shutters. Dimensions and weights are authored, not surveyed.

- [Original Raiwaqa housing units](https://press-files.anu.edu.au/downloads/press/n10434/html/ch16.xhtml) — [viewed photograph](https://press-files.anu.edu.au/downloads/press/n10434/html/image/figure82.jpg). Low two-storey residential blocks with light walls, wide openings and shallow pitched roofs.

### 64. Antarctic and subantarctic stations

Stable ID: `antarctic_stations`. Routing example: Davis Station.

Davis station image shows brightly coloured simple rectangular service modules; station architecture, not vernacular housing. Parameters are authored interpretations, not measured survey statistics. Roof defaults and optional variants are described in the implementation section above; material families remain limited to supported assets.

Implemented controls: windows 1.05 m wide at 2.65 m bays; pitch prior 18–29 degrees; details: screens. Dimensions and weights are authored, not surveyed.

- [Davis Station buildings](https://www.antarctica.gov.au/news/stations/davis/2018/this-week-at-davis-1-june-2018/) — [viewed photograph](https://www.antarctica.gov.au/site/assets/files/28948/davis-buildings.1200x0.jpg). Blue, green, orange and yellow rectangular clad service modules on a snowy rocky site.


## Personal detail audit

Ordinary regional windows now use wider bays and a per-storey glazed-area budget tied to wall area and opening size. Side/rear elevations receive extra spacing. Larger grouped windows therefore occupy fewer bays, while dedicated shopfront and office layouts retain their own rules. Across the same 64 two-storey comparison houses, opening count fell from 1,311 to 974 (26%). Entrance elevations receive a fuller two-to-three-window rhythm per floor on these 12 m fixtures, with windows fitted into clear spans around the door. The primary agent personally checked all four updated 16-theme overview sheets. The dimensions listed above are authored profile inputs, before grammar and density adjustments; they are not final facade spacing.

The primary agent personally reviewed all 64 themes against locality photographs and actual generated front/rear views, then rechecked all 64 after corrections. The review covers all four elevations. It is an offline mesh and proportion audit, with approximate material colours; native BeamNG acceptance remains pending.

The polish joins horizontal trims and roof caps through shared miter points, aligns structural accents with clear wall piers, gives gables the upper-wall material, corrects near/lite overlay depth and material UV scales, and distributes repeated details across complete elevations. Region-specific refinements remove unsupported roof choices, excessive glazing, arbitrary material splits and inappropriate all-storey arcades. The 64 individual decisions are stored in each profile under `personal_review`; the local evidence is `build/regional-runtime/personal-audit.json` and `personal-audit-final`. Research-photo sheets are not redistributed in the playtest.
