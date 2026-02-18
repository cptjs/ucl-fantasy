import React from 'react'

// UEFA team logo CDN - verified IDs from uefa.com/uefachampionsleague/clubs/
const LOGO_MAP = {
  'Real Madrid': 50051, 'RMA': 50051,
  'Barcelona': 50080, 'BAR': 50080,
  'Bayern München': 50037, 'BAY': 50037,
  'Liverpool': 7889, 'LIV': 7889,
  'Paris': 52747, 'PSG': 52747,
  'Man City': 52919, 'MCI': 52919,
  'Inter': 50138, 'INT': 50138,
  'B. Dortmund': 52758, 'BVB': 52758,
  'Juventus': 50139, 'JUV': 50139,
  'Atleti': 50124, 'ATM': 50124,
  'Arsenal': 52280, 'ARS': 52280,
  'Leverkusen': 50109, 'LEV': 50109,
  'Benfica': 50147, 'BEN': 50147,
  'Monaco': 50023, 'MON': 50023,
  'Atalanta': 52816, 'ATA': 52816,
  'Club Brugge': 50043, 'BRU': 50043,
  'Newcastle': 59324, 'NEW': 59324,
  'Galatasaray': 50067, 'GAL': 50067,
  'Olympiacos': 2610, 'OLY': 2610,
  'Sporting CP': 50149, 'SPO': 50149,
  'Bodø/Glimt': 59333, 'BOD': 59333,
  'Qarabağ': 60609, 'QAR': 60609,
  'AC Milan': 50058, 'MIL': 50058,
  'Chelsea': 52914, 'CHE': 52914,
  'Tottenham': 1652, 'TOT': 1652,
  'Celtic': 50050, 'CEL': 50050,
  'PSV': 50062, 'PSV': 50062,
}

function getLogoUrl(club) {
  const id = LOGO_MAP[club]
  if (id) {
    return `https://img.uefa.com/imgml/TP/teams/logos/100x100/${id}.png`
  }
  return null
}

export default function ClubLogo({ club, size = 20, className = '' }) {
  const url = getLogoUrl(club)
  
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
