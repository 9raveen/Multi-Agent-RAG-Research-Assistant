import "./BB8Toggle.css";

// BB8 droid day/night toggle, repurposed as the site's dark/light mode
// switch. Unchecked = day (light mode), checked = night (dark mode) —
// matches the toggle's own built-in sky gradient + stars/clouds animation.
//
// size="sm" applies the compact modifier for tight spaces (nav bars,
// sidebars). Omit it to use the full ~170x90px design.
export default function BB8Toggle({ theme, onToggle, size, className = "" }) {
  const isDark = theme === "dark";
  const sizeClass = size === "sm" ? "bb8-toggle--sm" : "";

  return (
    <label className={`bb8-toggle ${sizeClass} ${className}`}>
      <input
        className="bb8-toggle__checkbox"
        type="checkbox"
        checked={isDark}
        onChange={onToggle}
        aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      />
      <div className="bb8-toggle__container">
        <div className="bb8-toggle__scenery">
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="bb8-toggle__star"></div>
          <div className="tatto-1"></div>
          <div className="tatto-2"></div>
          <div className="gomrassen"></div>
          <div className="hermes"></div>
          <div className="chenini"></div>
          <div className="bb8-toggle__cloud"></div>
          <div className="bb8-toggle__cloud"></div>
          <div className="bb8-toggle__cloud"></div>
        </div>
        <div className="bb8">
          <div className="bb8__head-container">
            <div className="bb8__antenna"></div>
            <div className="bb8__antenna"></div>
            <div className="bb8__head"></div>
          </div>
          <div className="bb8__body"></div>
        </div>
        <div className="artificial__hidden">
          <div className="bb8__shadow"></div>
        </div>
      </div>
    </label>
  );
}
