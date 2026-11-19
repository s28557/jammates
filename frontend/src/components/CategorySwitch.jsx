import { useLayoutEffect, useRef } from 'react'

// Segmented switch with a frame that slides under the active option
export function CategorySwitch({ label, onChange, options, value }) {
  const containerRef = useRef(null)
  const indicatorRef = useRef(null)
  const layoutKey = options.map((option) => `${option.value}:${option.count ?? ''}`).join('|')

  // Move the frame to the active option, and keep it there on resize
  useLayoutEffect(() => {
    const container = containerRef.current
    const indicator = indicatorRef.current

    const placeIndicator = () => {
      const active = container.querySelector('[aria-checked="true"]')

      if (!active) {
        return
      }

      indicator.style.width = `${active.offsetWidth}px`
      indicator.style.transform = `translateX(${active.offsetLeft}px)`
    }

    placeIndicator()

    // Animate only after the first placement, so the frame doesn't slide in on load
    const frame = requestAnimationFrame(() => indicator.classList.add('category-switch-indicator-animated'))
    const observer = new ResizeObserver(placeIndicator)
    observer.observe(container)

    return () => {
      cancelAnimationFrame(frame)
      observer.disconnect()
    }
  }, [layoutKey, value])

  return (
    <div
      aria-label={label}
      className={`category-switch category-switch-${value}`}
      ref={containerRef}
      role="radiogroup"
    >
      <span aria-hidden="true" className="category-switch-indicator" ref={indicatorRef} />
      {options.map((option) => (
        <button
          aria-checked={option.value === value}
          key={option.value}
          onClick={() => onChange(option.value)}
          role="radio"
          type="button"
        >
          {option.label}
          {option.count !== undefined && <span className="category-switch-count">{option.count}</span>}
        </button>
      ))}
    </div>
  )
}
