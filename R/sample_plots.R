library(ggplot2)
library(zoo)
library(plyr)

dir = './' #THIS MUST HAVE A TRAILING SLASH
basename = 'avro'

issues = read.csv(paste(dir, basename, '-issues.csv', sep = ''), header = T)
p = ggplot(data = issues, aes(x = status, y = days_in_current_status))
p = p + geom_boxplot() + geom_jitter(aes(color = priority), alpha = 0.5)
p = p + labs(x = 'Status', y = 'Number of days', title = 'Number of days issues are in their current status')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
p = ggplot(data = transitions[transitions$to_status == 'Resolved',], aes(x = days_since_open, y = comment_count, color = priority))
p = p + geom_point()
p = p + labs(x = '# of days from open to resolved', y = '# of comments on issue', title = 'Days from open to resolution vs. comment count')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
transitions$month = strftime(as.POSIXct(transitions$when), '%Y-%m')
p = ggplot(data = transitions[transitions$to_status == 'Closed',], aes(x = as.factor(month), y = days_since_open))
p = p + geom_boxplot() + geom_jitter(alpha = 0.3)
p = p + labs(x = 'month', y = '# of days from open to close', title = '# of days it took to close issues closed in each month')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
transitions$month = strftime(as.POSIXct(transitions$when), '%Y-%m')
transitions = transitions[transitions$month > '2012-05',]
p = ggplot(data = transitions[transitions$to_status == 'Resolved',], aes(x = as.factor(month), y = days_since_open))
p = p + geom_boxplot() + geom_jitter(alpha = 0.3)
p = p + labs(x = 'month', y = '# of days from open to resolved', title = '# of days it took to resolve issues resolved in each month')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
transitions$week = strftime(as.POSIXct(transitions$when), '%Y-%U')
transitions = transitions[transitions$week > '2013',]
p = ggplot(data = transitions[transitions$to_status == 'Resolved',], aes(x = as.factor(week), y = days_since_open))
p = p + geom_boxplot() + geom_jitter(alpha = 0.3)
p = p + labs(x = 'week', y = '# of days from open to resolved', title = '# of days it took to resolve issues resolved in each week')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
p = ggplot(data = transitions[transitions$to_status == 'Resolved',], aes(x = as.POSIXct(when), y = days_since_open))
p = p + geom_point()
p = p + labs(x = 'day', y = '# of days from open to resolved', title = '# of days it took to resolve issues resolved per day')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
transitions = transitions[transitions$to_status == 'Closed',]
transitions$month = strftime(as.POSIXct(transitions$when), '%Y-%m')
closed = ddply(transitions, c('month', 'priority'), function(x) c(count = nrow(x)))
p = ggplot(data = closed, aes(x = as.factor(month), y = count, fill = priority))
p = p + geom_bar(stat = 'identity')
p = p + labs(x = 'Month', y = '# of closed issues', title = 'Issues closed per month')
print(p)

transitions = read.csv(paste(dir, basename, '-transitions.csv', sep = ''), header = T)
transitions = transitions[transitions$to_status == 'Resolved',]
transitions = transitions[as.character(transitions$when) > '2012',]
transitions$month = strftime(as.POSIXct(transitions$when), '%Y-%m')
closed = ddply(transitions, c('month', 'priority'), function(x) c(count = nrow(x)))
p = ggplot(data = closed, aes(x = as.factor(month), y = count, fill = priority))
p = p + geom_bar(stat = 'identity')
p = p + labs(x = 'Month', y = '# of resolved issues', title = 'Issues resolved per month')
print(p)

counts = read.csv(paste(dir, basename, '-daycounts.csv', sep = ''), header = T)
counts$day = as.POSIXct(counts$day)
p = ggplot(data = counts, aes(x = day, y = count))
p = p + geom_line() + geom_smooth(color = 'red', fill = NA, alpha = 0.5) + facet_grid(status ~ .)
p = p + labs(x = 'Time', y = '# of issues', title = 'Number of issues per status over time')
print(p)

counts = read.csv(paste(dir, basename, '-daycounts.csv', sep = ''), header = T)
counts$day = as.POSIXct(counts$day)
counts$status = factor(counts$status, levels = c('Open', 'In Progress', 'Patch Available', 'Resolved', 'Closed', 'Reopened'))
p = ggplot(data = counts, aes(x = day, y = count, fill = status))
p = p + geom_area()
p = p + labs(x = 'Time', y = '# of issues', title = 'Number of issues per status over time (stacked)')
print(p)

counts = read.csv(paste(dir, basename, '-daycounts.csv', sep = ''), header = T)
counts$day = as.POSIXct(counts$day)
counts = counts[as.character(counts$day) > '2013-04-01',]
counts = counts[counts$status != 'Closed',]
counts$status = factor(counts$status, levels = c('Open', 'In Progress', 'Patch Available', 'Resolved', 'Closed', 'Reopened'))
p = ggplot(data = counts, aes(x = day, y = count, fill = status))
p = p + geom_bar(stat = 'identity')
p = p + labs(x = 'Day', y = '# of issues', title = 'Number of issues per status since April 1st (stacked, w/o Closed)')
print(p)
