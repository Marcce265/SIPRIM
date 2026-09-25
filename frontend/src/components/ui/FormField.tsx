import type { InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from 'react'

interface BaseFieldProps {
  label: string
  error?: string
  className?: string
  children?: ReactNode
}

type InputFieldProps = BaseFieldProps &
  InputHTMLAttributes<HTMLInputElement> & {
    as?: 'input'
  }

type TextAreaFieldProps = BaseFieldProps &
  TextareaHTMLAttributes<HTMLTextAreaElement> & {
    as: 'textarea'
  }

export type FormFieldProps = InputFieldProps | TextAreaFieldProps

export function FormField(props: FormFieldProps) {
  const { label, error, className = '', as = 'input', ...rest } = props
  const spanClass = className.includes('span-2') ? 'form-field span-2' : 'form-field'

  return (
    <label className={spanClass}>
      <span className="form-field-label">{label}</span>
      {as === 'textarea' ? (
        <textarea
          className="form-field-input"
          aria-invalid={Boolean(error)}
          {...(rest as TextareaHTMLAttributes<HTMLTextAreaElement>)}
        />
      ) : (
        <input
          className="form-field-input"
          aria-invalid={Boolean(error)}
          {...(rest as InputHTMLAttributes<HTMLInputElement>)}
        />
      )}
      {error && <em className="form-field-error">{error}</em>}
    </label>
  )
}
