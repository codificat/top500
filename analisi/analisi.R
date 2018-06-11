# Carreguem les dades, corregint tipus d'atributs quan cal
col.classes <- c(
    'site_id'     = 'factor',
    'system_id'   = 'factor',
    'name'        = 'character',
    'site_name'   = 'character',
    'system_url'  = 'character',
    'site_url'    = 'character'
)
top500 <- read.csv('../data/top500.csv',
                   na.strings = '',
                   colClasses = col.classes)
str(top500)

# Descartem variables que no són útils per l'anàlisi de les dades.
# Mantenim system_id per si ens cal identificar un mateix sistema
# a diverses edicions de la llista.
descarta <- c('site_id', 'name', 'site_name', 'system_url', 'site_url')
top500 <- top500[ , !(names(top500) %in% descarta) ]

# Creem una funcio per ajuntar els valors que coincideixen amb un patro.
# Tots els factors que coincideixin amb el patró seran substituïts pel
# nou valor
mergelevels <- function(x, pattern, newvalue, ...) {
  # aquesta funció només modifica valors categòrics
  if (class(x) == "factor") {
    sel <- grep(pattern, levels(x), ...)
    levels(x)[ sel ] <- newvalue
  }
  x
}

# Creem un nou camp "list" que contingui la data de la llista
top500$list <- as.Date(
    ISOdate(top500$year, top500$month, 1, c(0,12))
)
# Creem un nou camp "edition" amb el número d'edició de la llista
# (la primera llista que es va publicar serà la edició número 1, etc)
top500$edition <- factor(top500$list)
levels(top500$edition) <- order(levels(top500$edition))
top500$edition <- as.integer(top500$edition)

# Eliminem la variable month, que ja no farem servir
top500 <- subset(top500, select = -month)

# Veure com hi ha un canvi d'ordre de magnitud a rmax
top500[top500$rank == 1 & top500$month == 6, c('year', 'rmax')]

# Passem les mesures més recents, que estan en TFlops, a GFlops per
# tal que els valors de rmax i rpeak estiguin en la mateixa unitat
top500[top500$edition > 24, 'rmax'] <- 1000 *
    top500[top500$edition > 24, 'rmax']
top500[top500$edition > 24, 'rpeak'] <- 1000 *
    top500[top500$edition > 24, 'rpeak']

# Ens guardem quants fabricants diferents hi ha a les dades originals
fabricants <- nlevels(top500$manufacturer)

# Unifiquem noms de fabricants
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   '^Cray', 'Cray')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   '^Dell', 'Dell', ignore.case = TRUE)
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   '^(IBM|Lenovo)', 'IBM')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   '^(HP|Hewlett)', 'HP')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'Fujitsu', 'Fujitsu')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'NEC', 'NEC')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'Hitachi', 'Hitachi')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'ClusterVision', 'ClusterVision')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'T-Platforms', 'T-Platforms')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'NSSOL', 'NSSOL')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'SGI|Networx', 'SGI')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'Kendall|KSR', 'KSR')
top500$manufacturer <- mergelevels(top500$manufacturer, 'Raytheon',
                                   'Raytheon-Aspen Systems')
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'supermicro', 'SuperMicro',
                                   ignore.case = TRUE)
# Unifiquem diversos dissenys propis del NRCPC a la Xina
top500$manufacturer <- mergelevels(top500$manufacturer,
                                   'NRCPC|National Research|University',
                                   'Self-made')

# Agrupem diferents versions d'un mateix sistema operatiu
top500$os <- mergelevels(top500$os, 'OSF/1', 'OSF/1')
top500$os <- mergelevels(top500$os, 'Windows', 'Windows')
top500$os <- mergelevels(top500$os, 'UNICOS', 'UNICOS')
top500$os <- mergelevels(top500$os, 'Ubuntu', 'Ubuntu')
top500$os <- mergelevels(top500$os, 'bullx', 'Bullx', ignore.case = TRUE)
top500$os <- mergelevels(top500$os, 'redhat|rhel',
                         'Red Hat Enterprise Linux',
                         ignore.case = TRUE)
top500$os <- mergelevels(top500$os, 'suse|SLES', 'SuSE Linux',
                         ignore.case = TRUE)

# El resum del data frame ens permet veure quines variables
# contenen NAs
summary(top500)

# Descartem la vairable gpu pel seu elevat nombre de valors
# nuls i invàlids
top500 <- subset(top500, select = -gpu)

# Comprovem que només tenim valors d'hpcg per les edicions recents
table(top500[! is.na(top500$hpcg), "edition" ])

# Descartem la vairable hpcg pel seu elevat nombre de valors
# buits i la seva nul·la presència a les primeres 34 edicions
top500 <- subset(top500, select = -hpcg)

# Corregir el valor del factor "N/A" reemplaçant-lo per NA
# a les variable os i compiler
top500[!is.na(top500$os) & top500$os == "N/A", "os"] <- NA
top500[!is.na(top500$compiler) & top500$compiler == "N/A", "compiler"] <- NA
# Desfer-nos de la categoria "N/A" ara que està buida
top500$os <- factor(top500$os)
top500$compiler <- factor(top500$compiler)

# Boxplot de rmax i cores i els seu logaritme, un al costat de l'altre
par(mfrow=c(2,2))
boxplot(top500$rmax, xlab = "rmax")
boxplot(log(top500$rmax), xlab = "log(rmax)")
boxplot(top500$cores, xlab = "cores")
boxplot(log(top500$cores), xlab = "log(cores)")

# Agrupació de sistemes operatius per families
top500$osfamily <- top500$os

linux <- c(
    'Linux', 'Ubuntu', 'CentOS', 'Bullx', 'RaiseOS', 'TOSS', 'CNL'
)
top500$osfamily <- mergelevels(top500$osfamily,
                               paste0(linux, collapse="|"),
                               'Linux', ignore.case = TRUE)

unix <- c(
    'AIX', 'IRIX', 'HP', 'Unix', 'CMOST', 'Solaris', 'SunOS',
    'MacOS', 'HI-UX', 'Ultrix', 'PARIX', 'Super-UX', 'UNICOS',
    'ConvexOS', 'SPP-UX', 'Tru64', 'OSF/1', 'KSR', 'EWS', 'UXP'
)
top500$osfamily <- mergelevels(top500$osfamily,
                               paste0(unix, collapse = "|"),
                               'Unix', ignore.case = TRUE)

other <- c('Cell OS', 'CRS-OS', 'NX/2', 'Paragon')
top500$osfamily <- mergelevels(top500$osfamily,
                               paste0(other, collapse="|"),
                               'Other')
table(top500$osfamily)

# Desem les dades pre-processades
write.csv(top500, '../data/top500-clean.csv', row.names = FALSE)

# Diagrames de punts per parelles de les variables numèriques
# candidates a comparar
pairs(~ rmax + cores + memory + power, data = top500, log = "xy")

# Visualitzem la potència de càlcul de l'últim ordinador de cada
# edició de la llista TOP500
bottom500 <- top500[top500$rank == 500, ]
with(bottom500, plot(edition, rmax))

# Regressió entre rmax i cores
rmaxcores <- lm(log10(top500$rmax) ~ log10(top500$cores))
summary(rmaxcores)

# Regressió entre rmax i memory
rmaxmem <- lm(log10(top500$rmax) ~ log10(top500$memory))
summary(rmaxmem)

# Regressió entre rmax i power
rmaxpower <- lm(log10(top500$rmax) ~ log10(top500$power))
summary(rmaxpower)

library(ggplot2)
# Dibuixem l'evolució del rendiment del primer i últim ordinador de
# cada llista al llarg del temps. Segons la llei de Moore aquesta
# progressió és exponencial, i per tant fem servir una escala logarítmica
# a l'eix del rendiment. Hi dibuixem també models lineals per
# visualitzar millor l'evolució
ggplot(data = top500[top500$rank == 1 | top500$rank == 500, ],
       aes(x = edition, y = rmax, colour = factor(rank))) +
    labs(x = 'Edició de la llista', y = 'Rendiment (rmax GFlop/s)',
         colour = 'Posició') +
    geom_point() +
    geom_smooth(data = top500[top500$rank == 1,], method = 'lm') +
    geom_smooth(data = top500[top500$rank == 500,], method = 'lm') +
    scale_y_log10()

# rmax vs cores
ggplot(data = top500, aes(x = rmax, y = cores)) +
    geom_point() + geom_smooth() +
    scale_x_log10() + scale_y_log10()

# rmax vs memory
ggplot(data = top500[top500$rmax > 1000,], aes(x = rmax, y = memory)) +
    geom_point() + geom_smooth(se = FALSE) +
    scale_x_log10() + scale_y_log10()

# rmax vs power
ggplot(data = top500[top500$rmax > 1000,], 
       aes(x = rmax, y = power)) +
    geom_point() + geom_smooth(se = FALSE) +
    scale_x_log10() + scale_y_log10()

# power vs cores
ggplot(data = top500[top500$cores > 100,], aes(x = cores, y = power)) +
    geom_point() + geom_smooth(method = "lm") +
    scale_x_log10() + scale_y_log10()
