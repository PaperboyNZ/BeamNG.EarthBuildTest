# Regional architectural themes: 64-pack catalogue

Current regional detail authoring: [25 architectural modifiers and spawn rates](REGIONAL_ARCHITECTURAL_MODIFIERS.md).

Current roof authoring: [roof proportions, attic windows and dormers](ROOF_PROPORTIONS_AND_ATTICS.md). Shared inference limits apply across all 64 regional profiles and five contemporary families; tall eligible roofs receive fitted attic details. Historical checkpoint statements below retain their original scope.

Expanded on 1 November 2026. The source of truth is `server/buildgen/catalog/environments.json`.

**All 64 themes now have active parameterized regional grammars and geographic routing.**

See [runtime behavior, image references and validation](REGIONAL_THEME_RUNTIME.md) for the implementation. The table below retains the broader architectural design directions; advanced forms such as courtyards, traditional roof systems and sacred/ceremonial detailing still require specific evidence and additional geometry.

The 64 slots cover North America (9), Latin America/Caribbean (8), Europe (12), Africa (9), West/Central Asia (7), South Asia (5), East Asia (5), Southeast Asia (4), Oceania (4), and Antarctica/subantarctic (1).

## Generic large-block proposals

The approved A/B/C designs now have a bounded generic-block implementation; see
[runtime behaviour, exclusions and verification](REGIONAL_BLOCK_IMPLEMENTATION.md).
All 192 variants are selectable for eligible generic rectangular buildings.
The catalogue below retains the original design briefs and conditional upgrades.

[Review the illustrated catalogue](regional-block-proposals.html) or the
[full text proposals](REGIONAL_BLOCK_PROPOSALS.md): **three multi-purpose designs
per theme, 192 proposals total**. These are derived from the written directions
below, independently of the unfinished runtime style implementations. Each covers
facade composition, materials, entrances, roof edges, controlled procedural
variation and supported geometry upgrades. Prepared commercial properties are
outside scope. This is a design catalogue, not a generator or playtest update.
The [structured catalogue](regional-block-proposals.json) retains stable proposal
IDs and the source text for later implementation.

## Catalogue

Status: **R** = active regional grammar and geographic routing; broader design directions are not all bespoke implemented geometry.

### North America

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | **US Northeast** (`us_northeast`) | New England and the Mid-Atlantic; NYC adapter footprint only at runtime | Federal and Georgian townhouses; brick rowhouses and brownstones; timber suburbs and contemporary infill | Stoops, aligned sash bays, cornices and restrained shopfront insertion | R |
| 2 | **US Southeast and Gulf** (`us_southeast`) | Southeastern states, Appalachia and the Gulf Coast | Porch houses and shotgun houses; Appalachian timber homes; brick ranch and contemporary suburban stock | Porch depth, screened openings and climate-specific eaves | R |
| 3 | **US Midwest and Great Plains** (`us_midwest`) | Great Lakes, central plains and interior US Rockies | Worker cottages and brick two-flats; Prairie and Craftsman houses; farmsteads and postwar ranches | Broad eaves, masonry bases and distinct urban/rural frontage rhythms | R |
| 4 | **US Southwest** (`us_southwest`) | Desert Southwest and inland southern California | Pueblo Revival; Spanish Colonial Revival; desert modern and ordinary stucco suburbs | Recessed openings, shaded courts and separately evidenced parapets | R |
| 5 | **US Pacific Coast** (`us_pacific`) | Coastal California, Oregon and Washington | Craftsman and timber vernacular; California Spanish Revival; mid-century and contemporary coastal infill | Porches, projecting bays, siding and local flat/pitched roof variants | R |
| 6 | **Atlantic Canada and Quebec** (`canada_atlantic`) | Maritime provinces, Newfoundland, Quebec and eastern Ontario | Maritime timber houses; Quebec stone and brick streets; duplexes and contemporary infill | Painted siding, dormers, exterior stairs only where evidenced. Reference: [UNESCO: Old Town Lunenburg](https://whc.unesco.org/en/list/741/) | R |
| 7 | **Canadian Prairies and interior** (`canada_prairie`) | Prairie provinces, inland British Columbia and northern Ontario | Prairie farmhouses; railway-town brick main streets; bungalows and modern infill | Wind lobbies, compact envelopes and shopfront/parapet variation | R |
| 8 | **Coastal British Columbia** (`canada_pacific`) | Pacific Canadian settlements and coastal islands | Timber coastal vernacular; Arts and Crafts; West Coast modern and mixed-use infill | Rain-sheltered entries, wood cladding and deep glazed bays | R |
| 9 | **Alaska, northern Canada and Greenland** (`arctic_north_america`) | Arctic/subarctic settlements including Greenland; separate local communities | Painted timber settlements; compact insulated modular housing; contemporary Arctic civic buildings | Wind vestibules, insulated panels and surveyed foundation clearances | R |

### Latin America and Caribbean

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 10 | **Mexico and northern Mesoamerica** (`latin_american_local`) | Mexico and adjoining highland settlement traditions; locality-specific | Courtyard and adobe traditions; colonial masonry streets; modernist and incremental urban housing | Recessed entries, courtyard-facing galleries and separately mapped roof terraces | R |
| 11 | **Caribbean and Atlantic island towns** (`caribbean_creole`) | Greater/Lesser Antilles, Bahamas, Bermuda and Caribbean coastal enclaves | Creole timber houses; Spanish courtyard streets; Art Deco and reinforced-concrete urban stock | Louvres, shaded galleries, hurricane shutters and local roof profiles | R |
| 12 | **Central American isthmus** (`central_america`) | Guatemala through Panama, including Belize and both coasts | Highland courtyard houses; Caribbean timber settlements; tropical modern and ordinary concrete housing | Verandas, covered circulation and highland/coastal material separation | R |
| 13 | **Andean highlands** (`andean_highlands`) | Colombia, Ecuador, Peru and Bolivia highland settlements | Adobe and stone courtyard houses; colonial urban blocks; brick and concrete self-built neighbourhoods | Thick reveals, sheltered courts and local tile/metal roof choices | R |
| 14 | **Coastal and southeastern Brazil** (`brazil_coastal`) | Atlantic Brazil, including northeast, southeast and southern coastal cities | Portuguese-derived townhouses; Art Deco streets; Brazilian modernism and contemporary apartments | Shaded balconies, cobogo-inspired screens and ordinary rendered facades | R |
| 15 | **Amazon and Guianas** (`amazon_guianas`) | Amazon basin, inland tropical lowlands, Guyana, Suriname and French Guiana | Riverine timber housing; Guianese veranda houses; contemporary lowland masonry settlements | Ventilated eaves, rain protection and raised floors only with evidence | R |
| 16 | **Southern Cone plains and Patagonia** (`southern_cone`) | Argentina, Uruguay, Paraguay and inland southern Brazil; Patagonian localities | Patio and chorizo houses; Italianate urban fronts; modernist blocks and Patagonian timber/metal homes | Courtyard sequences, rhythmic cornices and cold/warm locality variants | R |
| 17 | **Chilean Pacific settlements** (`chile_pacific`) | Chilean coast, central valleys, Chiloe and far-south settlements | Hillside port houses; Chilote timber and shingle traditions; contemporary seismic-frame housing | Stepped fronts within measured envelopes and timber/metal cladding. Reference: [UNESCO: Historic Quarter of Valparaiso](https://whc.unesco.org/en/list/959/) | R |

### Europe

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 18 | **Britain, Ireland and Atlantic islands** (`eu_atlantic`) | Britain, Ireland and locally verified Azores/Madeira traditions | Georgian and Victorian terraces; stone cottages; postwar estates and contemporary infill | Sash-bay rhythm, brick/stone reveals and local slate/tile distinctions | R |
| 19 | **Iberian Mediterranean and interior** (`eu_mediterranean`) | Spain, Portugal and Balearic settlements; local Atlantic variants | Patio houses; whitewashed and tiled urban fronts; modern apartment and suburban stock | Shutters, balconies, shaded courts and ceramic accents | R |
| 20 | **Nordic countries and North Atlantic** (`nordic_cold`) | Scandinavia, Finland, Iceland, Faroe Islands and Svalbard | Painted timber towns; Nordic classicism; functionalist housing and contemporary timber | Weather-protected entries, restrained trim and locality-specific roof systems | R |
| 21 | **France and regional traditions** (`france_regional`) | French mainland and Corsica; regional and urban/rural subdivisions | Haussmannian streets; half-timber and stone regional houses; modernist estates and contemporary infill | Mansard details only with roof support, shutters and rhythmic stone bays | R |
| 22 | **Low Countries** (`low_countries`) | Netherlands, Belgium and Luxembourg | Brick canal and merchant houses; Flemish terraces; modernist and contemporary brick housing | Narrow bay rhythms, gable variations and recessed entrances | R |
| 23 | **German-speaking and central Europe** (`central_europe`) | Germany, Czechia, Poland, Slovakia and non-Alpine Austria/Switzerland | Half-timber and masonry townhouses; perimeter blocks; postwar estates and contemporary housing | Rendered panels, brick trim, regular street walls and local roof pitches | R |
| 24 | **Alpine settlements** (`alpine`) | Alpine valleys and uplands across national borders | Timber chalet traditions; stone valley houses; contemporary Alpine apartments | Deep eaves, timber galleries and snow details only where validated | R |
| 25 | **Italian peninsula and islands** (`italy_regional`) | Italy, Sicily, Sardinia and Malta; separate local palettes | Palazzo and courtyard blocks; stone/stucco vernacular; rationalist and contemporary apartment buildings | Shutters, loggias, restrained cornices and island-specific stonework | R |
| 26 | **Adriatic and Balkan interior** (`adriatic_balkans`) | Slovenia, Croatia, Bosnia and Herzegovina, Serbia, Montenegro, Kosovo, Albania and North Macedonia | Adriatic stone streets; Ottoman-influenced timber/masonry houses; Yugoslav modernism and infill | Balconies, shaded loggias and coastal/interior roof differentiation | R |
| 27 | **Greece and Cyprus** (`aegean`) | Mainland Greece, Aegean islands and Cyprus | Island courtyard houses; neoclassical townhouses; polykatoikia apartment blocks | Shutters, balcony bands and locality-specific whitewash/stone treatment | R |
| 28 | **Eastern Europe and Baltic** (`eastern_europe`) | Estonia, Latvia, Lithuania, Belarus, Ukraine, Moldova, Romania, Bulgaria and Hungary | Timber and masonry vernacular; eclectic and Art Nouveau streets; socialist-era blocks and contemporary infill | Bay/cornice variation and explicit rural/urban distinctions | R |
| 29 | **Russia and northern Eurasia** (`russia_north`) | European Russia, Siberia and Russian Far East; local traditions required | Timber izba houses; classical and eclectic urban blocks; constructivist and panel housing | Carved trim only with support, panel rhythms and climate-specific entries | R |

### Africa

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 30 | **West African Atlantic and Gulf of Guinea** (`african_local`) | Coastal West Africa from Senegal to Nigeria; separate city/community variants | Compound houses; Afro-Brazilian urban fronts; tropical modern and contemporary masonry housing | Shaded galleries, ventilation screens and courtyard-facing openings | R |
| 31 | **Maghreb and northwest Africa** (`maghreb`) | Morocco, Algeria, Tunisia, Libya and locally verified Saharan/Canary settlements | Medina courtyard houses; Amazigh earthen and stone traditions; modern Mediterranean urban stock | Deep reveals, shaded courts and local tile/plaster detailing | R |
| 32 | **Sahel and western Sudanian belt** (`sahel`) | Mauritania, Mali, Burkina Faso, Niger, Chad and inland West African localities | Sudano-Sahelian earthen compounds; courtyard trading towns; contemporary masonry housing | Buttressed forms only with footprint support and shaded recessed openings. Reference: [UNESCO: Old Towns of Djenne](https://whc.unesco.org/en/list/116) | R |
| 33 | **Nile Valley and northeast desert** (`nile_valley`) | Egypt and Sudan; river, delta, Nubian and desert localities | Nubian courtyard traditions; urban masonry apartment blocks; modern concrete housing | Shading, deep reveals and separately evidenced vault/dome forms | R |
| 34 | **Horn of Africa and Ethiopian highlands** (`horn_africa`) | Ethiopia, Eritrea, Djibouti and Somalia with highland/coastal distinctions | Highland stone compounds; Asmara modernism; coastal and contemporary urban masonry | Local stone/render treatment, verandas and modernist horizontal bands. Reference: [UNESCO: Asmara](https://whc.unesco.org/en/list/1550) | R |
| 35 | **Swahili coast and East African interior** (`swahili_east_africa`) | Kenya, Tanzania, Uganda, Rwanda and Burundi; coast and lake/highland variants | Swahili courtyard townhouses; inland masonry and timber housing; tropical modern urban buildings | Carved-entry references, shaded verandas and coast/interior differentiation | R |
| 36 | **Central African forest and plateau** (`central_africa`) | Cameroon, Central African Republic, South Sudan, Equatorial Guinea, Gabon and both Congos | Forest timber compounds; veranda houses; contemporary blockwork and concrete cities | Rain-shedding eaves, ventilated screens and timber/masonry alternatives | R |
| 37 | **Southern African plateau and coasts** (`southern_africa`) | Angola, Zambia, Malawi, Mozambique, Zimbabwe, Botswana, Namibia, South Africa, Lesotho and Eswatini | Cape and veranda traditions; courtyard homesteads; modernist, township and contemporary suburban stock | Stoep/porch treatments, shade devices and separate highland/arid/coastal variants | R |
| 38 | **Madagascar and western Indian Ocean** (`indian_ocean_africa`) | Madagascar, Comoros, Mauritius, Reunion, Seychelles and nearby islands | Malagasy highland brick houses; coastal timber traditions; Creole veranda and contemporary concrete housing | Steep local roof variants, timber galleries and cyclone-conscious detailing | R |

### West and Central Asia

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 39 | **Arabian Peninsula and Gulf** (`arid_warm`) | Gulf states, Saudi Arabia, Oman and Yemen; distinct coastal/highland/desert variants | Courtyard and wind-tower traditions; Yemeni tower houses; contemporary villas and urban blocks | Screened openings, shaded courts and locally evidenced tower/roof forms. Reference: [UNESCO: Old Walled City of Shibam](https://whc.unesco.org/en/list/192/) | R |
| 40 | **Levant and eastern Mediterranean** (`levant`) | Lebanon, Syria, Jordan, Israel and Palestinian localities | Stone courtyard houses; arcaded urban fronts; modern apartment and suburban buildings | Limestone-like palettes, balconies and deep window reveals | R |
| 41 | **Anatolia and Caucasus** (`anatolia_caucasus`) | Turkiye, Armenia, Georgia and Azerbaijan; coastal/highland subdivisions | Timber Ottoman houses; Caucasian stone and balcony houses; modern apartment neighbourhoods | Projecting upper bays, shaded galleries and regional masonry details | R |
| 42 | **Iranian plateau and Afghan uplands** (`iran_plateau`) | Iran and Afghanistan; desert, mountain and Caspian localities | Courtyard and earthen traditions; Caspian timber houses; brick/concrete urban apartments | Recessed courts, local brick patterns and evidenced windcatchers. Reference: [UNESCO: Historic City of Yazd](https://whc.unesco.org/en/list/1544/) | R |
| 43 | **Mesopotamian plains** (`mesopotamia`) | Iraq and adjoining river plain localities | Courtyard brick houses; shanashil timber-front traditions; contemporary masonry and concrete blocks | Screened projecting bays, recessed entries and shaded passage fronts | R |
| 44 | **Central Asian oasis towns** (`central_asia_oases`) | Uzbekistan, Turkmenistan, Tajikistan and oasis settlements of neighbouring states | Earthen courtyard houses; brick merchant streets; Soviet-era and contemporary apartment stock | Courtyard orientation, restrained brick patterns and local timber galleries | R |
| 45 | **Central Asian steppe and mountain towns** (`central_asia_steppe`) | Kazakhstan, Kyrgyzstan and Mongolia; permanent settlements | Timber and masonry townhouses; Soviet-era apartment blocks; contemporary low-rise and urban infill | Wind-sheltered entries and permanent-building treatment of settlement edges | R |

### South Asia

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 46 | **Indus, Gangetic plains and western India** (`indus_gangetic`) | Pakistan, northern India, Rajasthan and Gujarat; explicit local subvariants | Haveli and pol courtyard houses; brick bazaar fronts; modern concrete and mixed-use neighbourhoods | Jali-inspired screens, shaded balconies and local timber/brick detail. Reference: [Ministry of Culture: Historic City of Ahmedabad](https://culture.gov.in/historic-city-ahmedabad2017) | R |
| 47 | **Peninsular India and Deccan** (`india_peninsular`) | Central, western and southern Indian peninsula | Deccan courtyard houses; Kerala/Malabar timber and tile traditions; modernist and contemporary concrete housing | Deep verandas, rain eaves and dry/wet locality distinction | R |
| 48 | **Bengal and northeast South Asia** (`bengal_delta`) | Bangladesh, eastern India, Assam and northeast Indian localities | Bengal courtyard and curved-roof traditions; raised timber/bamboo houses; brick and concrete urban stock | Monsoon eaves, shaded openings and mapped floor-height constraints | R |
| 49 | **Himalayan foothills and valleys** (`himalayan`) | Nepal, Bhutan and Indian/Pakistani Himalayan localities | Newar brick and timber houses; Bhutanese timber/masonry traditions; contemporary hill-town buildings | Timber bands, deep eaves and slope-aware fronts within source geometry | R |
| 50 | **Sri Lanka and Maldives** (`sri_lanka_maldives`) | Sri Lankan wet/dry zones and Maldivian islands | Courtyard and veranda houses; tropical modernism; island masonry and contemporary urban housing | Shaded colonnades, ventilation and tile/metal alternatives | R |

### East Asia

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 51 | **Japan and Ryukyu islands** (`jp_temperate`) | Japanese archipelago; Hokkaido, mainland and Okinawan subvariants | Machiya and minka traditions; postwar compact houses; contemporary narrow urban infill | Layered eaves, screened fronts and local tile/metal roof distinctions | R |
| 52 | **Northern and inland China** (`china_north`) | Northern plains, northeast China and northwestern inland towns | Siheyuan courtyard houses; brick hutong fronts; danwei and contemporary apartment stock | Courtyard gates, brick bays and cold-region enclosure | R |
| 53 | **Southern China, Taiwan and coastal cities** (`china_south`) | Southern/southwestern China, Hong Kong, Macao and Taiwan; local subvariants | Jiangnan courtyard houses; Lingnan qilou and Taiwanese shophouses; modern high-density and village stock | Arcaded fronts, rain eaves and separate hill/coast urban forms | R |
| 54 | **Korean peninsula** (`korea`) | North and South Korean localities, including Jeju | Hanok courtyard traditions; brick urban houses; modern apartment and mixed-use blocks | Courtyard-facing eaves, timber accents and ordinary contemporary facades | R |
| 55 | **Tibetan plateau and high mountain settlements** (`tibetan_plateau`) | Tibetan cultural plateau and adjoining high-altitude localities | Stone and rammed-earth courtyard houses; timber-trimmed highland homes; contemporary masonry town buildings | Deep reveals, local parapets and climate-specific compact openings | R |

### Southeast Asia

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 56 | **Malay Peninsula and equatorial trading towns** (`tropical_humid`) | Malaysia, Singapore and Brunei; local urban/rural variants | Malay timber houses; Straits shophouses; tropical modern and contemporary urban housing | Five-foot-way-inspired frontage, ventilated screens and rain eaves | R |
| 57 | **Mainland Southeast Asia** (`mainland_southeast_asia`) | Myanmar, Thailand, Laos, Cambodia and Vietnam | Timber stilt-house traditions; trading-port shophouses; tube houses and modern concrete neighbourhoods | Narrow frontage rhythms, shaded galleries and mapped raised floors. Reference: [UNESCO: Hoi An Ancient Town](https://whc.unesco.org/en/list/948) | R |
| 58 | **Indonesia and Timor** (`indonesian_archipelago`) | Indonesian islands and Timor-Leste; separate island/community variants | Javanese courtyard and pavilion traditions; Sumatran and Sulawesi timber forms; contemporary kampung masonry | Ventilated roof edges and distinctive roof silhouettes only with evidence | R |
| 59 | **Philippine archipelago** (`philippines`) | Luzon, Visayas and Mindanao; local settlement variants | Bahay kubo and bahay na bato traditions; Art Deco town fronts; contemporary concrete and mixed-use buildings | Shaded upper galleries, vent panels and local roof/eave systems | R |

### Oceania

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 60 | **New Zealand and temperate southern Pacific** (`nz_temperate`) | New Zealand settlements including Chatham Islands; Christchurch pilot only at runtime | Timber villas and bungalows; brick/render suburban houses; contemporary infill and locally evidenced Maori civic traditions | Weatherboards, sheltered porches and metal/tile roof distinctions | R |
| 61 | **Southeastern and temperate Australia** (`au_southeast`) | Southeastern Australia, Tasmania and temperate southwest settlements | Victorian terraces and Federation houses; brick veneer suburbs; contemporary coastal and urban infill | Verandas, ironwork references, local brick/render and metal/tile roofs | R |
| 62 | **Northern and inland Australia** (`au_tropical_arid`) | Tropical north, Queensland, inland arid regions and remote settlements | Queenslander timber houses; arid-region veranda buildings; tropical modern and contemporary modular housing | Deep shade, ventilation and separately evidenced elevated floors | R |
| 63 | **Melanesia, Micronesia and Polynesia** (`pacific_islands`) | Papua New Guinea, Pacific island states/territories and Hawaii; local subvariants | Community-specific timber/pavilion traditions; Pacific bungalow and plantation-era forms; contemporary island masonry housing | Open shaded edges, rain protection and cyclone-aware local roof profiles | R |

### Antarctica and subantarctic

| # | Theme / stable ID | Geographic scope | Architectural directions | Detail goals | Status |
| --- | --- | --- | --- | --- | --- |
| 64 | **Antarctic and subantarctic stations** (`antarctic_stations`) | Mapped research stations and field infrastructure, including southern ocean islands | Historic expedition timber huts; insulated modular stations; contemporary research and service buildings | Panel joints, wind vestibules and surveyed raised foundations. Reference: [Australian Antarctic Program: Buildings and structures](https://www.antarctica.gov.au/antarctic-operations/stations-and-field-locations/amenities-and-operations/buildings-and-structures/) | R |

## Evidence and remaining work

The [runtime reference register](REGIONAL_THEME_RUNTIME.md) contains a viewed photograph, concrete observations and limitations for every theme. All 64 profiles are enabled; administrative/locality polygons provide global routing. Detailed implementation and validation limits are recorded there.

Advanced geometry, additional local/era variants, new earth/bamboo/thatch materials and native game visual acceptance remain further work. These packs provide regional visual defaults while preserving observed building facts.
