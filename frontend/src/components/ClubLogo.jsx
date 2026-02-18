import React from 'react'

// UEFA team logo CDN pattern - uses club short codes
// Fallback: show club code text badge
const LOGO_MAP = {
  // Map club names and codes to UEFA image IDs
  'Real Madrid': 50051, 'RMA': 50051,
  'Barcelona': 50080, 'BAR': 50080,
  'Bayern München': 50037, 'BAY': 50037,
  'Liverpool': 7889, 'LIV': 7889,
  'Paris': 52747, 'PSG': 52747,
  'Man City': 52919, 'MCI': 52919,
  'Inter': 46, 'INT': 46,
  'B. Dortmund': 50064, 'BVB': 50064,
  'Juventus': 50139, 'JUV': 50139,
  'Atleti': 50124, 'ATM': 50124,
  'Arsenal': 52280, 'ARS': 52280,
  'Leverkusen': 50046, 'LEV': 50046,
  'Benfica': 50147, 'BEN': 50147,
  'Monaco': 50069, 'MON': 50069,
  'Atalanta': 52907, 'ATA': 52907,
  'Club Brugge': 50043, 'BRU': 50043,
  'Newcastle': 52267, 'NEW': 52267,
  'Galatasaray': 50136, 'GAL': 50136,
  'Olympiacos': 50137, 'OLY': 50137,
  'Sporting CP': 50149, 'SPO': 50149,
  'Bodø/Glimt': 2016968, 'BOD': 2016968,
  'Qarabağ': 457428, 'QAR': 457428,
  'AC Milan': 50058, 'MIL': 50058,
  'Feyenoord': 50062, 'FEY': 50062,
  'Celtic': 50184, 'CEL': 50184,
  'PSV': 50065, 'PSV': 50065,
}

function getLogoUrl(club, size = 40) {
  const id = LOGO_MAP[club]
  if (id) {
    return `https://img.uefa.com/imgml/TP/teams/logos/${size}x${size}/${id}.png`
  }
  return null
}

export default function ClubLogo({ club, size = 20, className = '' }) {
  const url = getLogoUrl(club, size <= 24 ? 40 : 100)
  
  if (!url) {
    return (
      <span className={`inline-flex items-center justify-center rounded bg-gray-700 text-[8px] font-bold text-gray-300 ${className}`}
        style={{ width: size, height: size }}>
        {(club || '??').slice(0, 3)}
      </span>
    )
  }

  return (
    <img 
      src={url} 
      alt={club} 
      className={`inline-block object-contain ${className}`}
      style={{ width: size, height: size }}
      onError={(e) => {
        e.target.style.display = 'none'
        e.target.nextSibling && (e.target.nextSibling.style.display = 'inline-flex')
      }}
    />
  )
}
