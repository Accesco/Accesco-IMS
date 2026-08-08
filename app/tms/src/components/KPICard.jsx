import React from 'react';
import Sparkline from './Sparkline';
import styles from '../styles/dashboard.module.css';

export default function KPICard({
  title,
  value,
  description,
  changeText,
  isPositive = true,
  icon: IconComponent,
  accentColor = '#2563eb',
  sparklineData = [40, 45, 42, 58, 62, 59, 72],
  onClick,
}) {
  return (
    <div
      className={styles.kpiCard}
      onClick={onClick}
      title={`Click to inspect details for ${title}`}
    >
      <div className={styles.kpiCardHeader}>
        <div
          className={styles.kpiIconWrapper}
          style={{
            backgroundColor: `${accentColor}18`,
            color: accentColor,
          }}
        >
          {IconComponent && <IconComponent size={20} />}
        </div>
        <Sparkline data={sparklineData} color={accentColor} />
      </div>

      <div className={styles.kpiValueRow}>
        <div className={styles.kpiValue}>{value}</div>
        {changeText && (
          <span
            className={`${styles.kpiChange} ${
              isPositive ? styles.changePos : styles.changeNeg
            }`}
          >
            {changeText}
          </span>
        )}
      </div>

      <div className={styles.kpiTitle}>{title}</div>
      <div className={styles.kpiDesc}>{description}</div>
    </div>
  );
}
