# Sentinel-2 Timelapse

<table>
<tr>
<td><img src="icon.png" alt="Logo du plugin" width="400"/></td>
<td>
<p>Le plugin <strong>Sentinel-2 Timelapse</strong> permet d'automatiser la <strong>recherche</strong>, la <strong>visualisation par frise temporelle (timelapse)</strong> et l'<strong>export de mosaïques d'imagerie satellite Sentinel-2 (L2A)</strong> via l'API STAC du <strong>Microsoft Planetary Computer</strong>. L'outil se base directement sur l'<strong>emprise visuelle active du canevas QGIS</strong>, ce qui le rend idéal pour l'analyse ciblée de zones restreintes et locales de type <strong>communes</strong>. Il génère un <strong>rapport HTML interactif autonome</strong> (exploitant <strong>Leaflet</strong> et <strong>JSZip</strong>) permettant une exploration fluide des dates et un téléchargement propre des sources organisées sous forme d'<strong>archives ZIP par date</strong>.</p>
</td>
</tr>
</table>

---

## Compatibilité

- **QGIS 3.32** (testé uniquement sur cette version).
Il est possible que le plugin fonctionne avec d’autres versions de QGIS, mais cela n’a pas été testé.

>⚠️ Aucune nouvelle version n’est prévue. 

- **Dépendances (incluses nativement avec QGIS) :**
  - PyQt5
  - QGIS Core / API
  - requests (bibliothèque Python pour l'API STAC)

> ⚠️ Aucune installation externe n’est nécessaire.

---

## Installation

1. Téléchargez la dernière version dans [Releases](https://github.com/LIEGEON-QGIS-PLUGINS/Sentinel2Timelapse-QGIS/releases) (ZIP).  
2. Dans QGIS, allez dans `Extensions > Installer une extension depuis un fichier ZIP`.  
3. Sélectionnez le fichier ZIP téléchargé et installez-le.  
4. Redémarrez QGIS si nécessaire.  

---

## Utilisation

1. Ouvrez le plugin via le menu `LiDAR Tools >  Sentinel-2 Timelapse`.  
2. Positionnez votre vue sur l'emprise géographique souhaitée (idéalement une commune ou une zone restreinte). 
3. Configurez la période de recherche et le pas temporel pour le timelapse.
4. Lancez la recherche des dalles disponibles sur l'emprise de l'écran. 
5. Générez et ouvrez le rapport HTML interactif pour manipuler la frise temporelle et télécharger les archives ZIP par date.

> ⚠️ **Attention :** le temps de génération dépend du nombre de dates et de dalles trouvées sur l'emprise.

---

## Licence

Ce plugin est fourni **“tel quel”**, sans garantie d’aucune sorte.  
Licence : MIT / Open-source.

---

## Renonciation

L’auteur **ne peut être tenu responsable** des dommages éventuels liés à l’utilisation du plugin ou aux données traitées.
