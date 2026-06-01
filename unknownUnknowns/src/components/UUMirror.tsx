type UUMirrorProps = {
  size?: number;
  className?: string;
};

/**
 * The "Mirror" UU mark: inverted U above-left, regular U below-right.
 * Stroke uses currentColor so it inherits text color.
 */
export default function UUMirror({ size = 64, className }: UUMirrorProps) {
  return (
    <svg
      viewBox="0 0 200 160"
      width={size}
      height={(size * 160) / 200}
      className={className}
      aria-label="Unknown Unknowns logo"
      role="img"
    >
      <path
        d="M30 80 v-40 a30 30 0 0 1 60 0 v40"
        fill="none"
        stroke="currentColor"
        strokeWidth="14"
        strokeLinecap="square"
      />
      <path
        d="M110 80 v40 a30 30 0 0 0 60 0 v-40"
        fill="none"
        stroke="currentColor"
        strokeWidth="14"
        strokeLinecap="square"
      />
    </svg>
  );
}
